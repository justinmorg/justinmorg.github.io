#!/usr/bin/env python3
"""
features.py — one pass over the annotated blocks, two flat tables.

Usage:
    python3 features.py LABEL=block.pgn [LABEL=block.pgn ...] \
        [--tc 180+2,300+0] [--user-map LABEL=username ...] [--out DIR]
        [--emit-fens all|elig_P|standing_threat]

Emits, into --out (default /home/claude/features/):

    moves.csv.gz    one row per *own* move; opponent context as columns
    games.csv       one row per game
    manifest.json   per-block provenance: counts, date range, filters, sha
    fens.csv.gz     only with --emit-fens; (gid, ply, block, fen)

FENs are off by default: ~70 bytes x 178k rows would triple moves.csv.gz for a
column almost every query ignores. When they are needed — multi-PV work, drill
building, eyeballing a position — `--emit-fens` writes them from the same pass,
so they cannot drift from the rows they describe. Do not reconstruct them with a
separate re-walk.

Everything downstream is a groupby on these. No engine required — the evals
already in the PGN plus python-chess is the whole dependency set.

Definitions are imported from, or copied verbatim from, `hanging.py` and
`outcomes.py` so that group-P rates, peak/trough buckets and endgame-entry
buckets reproduce from this table exactly. If a definition here ever drifts
from those scripts, this file is the one that is wrong.

Centipawn convention: **player's POV throughout**, matching hanging.py's
`cp_before_me`. Mate is +/-10000; see `mate_flag`.

Deliberately not computed here: first-major-deterioration ply, phase bands,
trajectory typologies. All are groupbys with tunable cutoffs — baking them in
means re-running the pass whenever a cutoff is argued over.

Cost: ~18 ms/game including all SEE and complexity columns.
"""
import csv
import gzip
import json
import os
import re
import subprocess
import sys
from collections import Counter

import chess
import chess.pgn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import USER, npm, parse_eval, see, threat_after, winprob  # noqa: E402
from outcomes import bucket_of, is_flag  # noqa: E402

CLK = re.compile(r"\[%clk\s+(\d+):(\d+):([\d.]+)\]")
EVAL_TAG = re.compile(r"\[%eval")
MATE_CP = 10000
STD_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
           chess.ROOK: 5, chess.QUEEN: 9}

MOVE_COLS = [
    # identity
    "block", "site", "user", "gid", "ply", "fullmove", "side",
    # game context
    "tc", "date", "my_elo", "opp_elo",
    # eval
    "cp_before", "cp_after", "drop_cp", "wp_before", "wp_after", "wp_error",
    "mate_flag",
    # clock
    "clk", "opp_clk", "spend", "clk_diff",
    # phase / material
    "npm_light", "npm_std", "mat_bal", "queens_on", "is_endgame", "elig_P",
    # threat / SEE
    "see_standing", "see_after", "hang_label", "in_check",
    # complexity
    "n_legal", "n_checks_avail", "n_caps_avail", "n_opp_caps", "king_attackers",
    # opponent's previous move
    "opp_prev_san", "opp_prev_kind", "opp_created_threat",
    "opp_prev_was_recapture", "opp_prev_spend",
]

GAME_COLS = [
    "gid", "block", "site", "user", "tc", "date", "color", "my_elo", "opp_elo",
    "result", "score", "termination", "is_flag", "n_plies", "n_own_moves",
    "n_elig", "peak", "trough", "eg_entry_cp", "eg_entry_ply", "final_cp",
    "opening", "eco", "bucket",
]


def secs(comment):
    m = CLK.search(comment or "")
    if not m:
        return None
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def tc_parts(tc):
    """'180+2' -> (180, 2); '300' -> (300, 0)."""
    if "+" in tc:
        b, i = tc.split("+", 1)
        return int(b), int(i)
    try:
        return int(tc), 0
    except ValueError:
        return None, 0


def site_of(game):
    s = (game.headers.get("Site", "") or "").lower()
    if "lichess" in s:
        return "lichess"
    if "chess.com" in s or "chesscom" in s:
        return "chesscom"
    return "unknown"


def mat_balance(board, me):
    """Material balance in pawns, player POV, 1/3/3/5/9."""
    t = 0
    for pt, val in STD_VAL.items():
        t += val * (len(board.pieces(pt, chess.WHITE))
                    - len(board.pieces(pt, chess.BLACK)))
    return t if me == chess.WHITE else -t


def king_attackers(board, me):
    """Enemy attackers on squares adjacent to my king."""
    k = board.king(me)
    if k is None:
        return 0
    n = 0
    for sq in chess.scan_forward(chess.BB_KING_ATTACKS[k]):
        n += len(board.attackers(not me, sq))
    return n


def standing_threat(board):
    """Max SEE the *opponent* could win if I did nothing (null-move probe).

    Verbatim from hanging.py::probe — valid even when in check, which makes the
    position technically illegal, so king captures are excluded.
    """
    nb = board.copy(stack=False)
    nb.push(chess.Move.null())
    my_king = board.king(board.turn)
    best = 0
    for m in nb.legal_moves:
        if not nb.is_capture(m) or m.to_square == my_king:
            continue
        best = max(best, see(nb, m))
    return best


def opp_move_kind(board, move):
    """Structural class of an opponent move. Priority: check > capture >
    pawn_break > quiet. Deliberately independent of `opp_created_threat`,
    since a capture can also be a check and also create a threat."""
    if board.gives_check(move):
        return "check"
    if board.is_capture(move):
        return "capture"
    if board.piece_type_at(move.from_square) == chess.PAWN:
        after = board.copy(stack=False)
        after.push(move)
        them = board.turn
        for sq in chess.scan_forward(after.attacks_mask(move.to_square)):
            p = after.piece_at(sq)
            if p and p.color != them and p.piece_type == chess.PAWN:
                return "pawn_break"
    return "quiet"


def scan(path, label, user, tcs, fen_sel=None):
    mrows, grows, fens = [], [], []
    st = Counter()
    plies_total = plies_evald = 0
    dates = []
    with open(path) as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            st["games"] += 1
            hw = game.headers.get("White", "")
            hb = game.headers.get("Black", "")
            me = chess.WHITE if user == hw else (chess.BLACK if user == hb else None)
            if me is None:
                st["dropped_user"] += 1
                continue
            tc = game.headers.get("TimeControl", "")
            if tcs and tc not in tcs:
                st["dropped_tc"] += 1
                continue
            st["matched"] += 1

            gid = game.headers.get("GameId", "")
            site = site_of(game)
            date = game.headers.get("UTCDate", game.headers.get("Date", "")).replace(".", "-")
            dates.append(date)
            my_elo = game.headers.get("WhiteElo" if me == chess.WHITE else "BlackElo", "")
            opp_elo = game.headers.get("BlackElo" if me == chess.WHITE else "WhiteElo", "")
            res = game.headers.get("Result", "")
            score = 0.5 if res == "1/2-1/2" else (
                1.0 if (res == "1-0") == (me == chess.WHITE) else 0.0)
            term = game.headers.get("Termination", "?")
            base, inc = tc_parts(tc)

            board, node, prev = game.board(), game, 0
            ply = 0
            peak, trough, n_elig = -10 ** 9, 10 ** 9, 0
            eg_cp, eg_ply, last_cp = None, None, 0
            prev_own_clk = float(base) if base else None
            prev_own_see_after = None       # for opp_created_threat
            prev_own_to = None              # for opp_prev_was_recapture
            pending_opp = None              # context of their move, awaiting mine
            prev_opp_clk = float(base) if base else None
            game_rows = []

            while node.variations:
                node = node.variations[0]
                move = node.move
                mover, fm = board.turn, board.fullmove_number
                ply += 1
                plies_total += 1
                if EVAL_TAG.search(node.comment or ""):
                    plies_evald += 1
                ev = parse_eval(node.comment, mover == chess.WHITE)
                clk = secs(node.comment)
                cp_before = prev if me == chess.WHITE else -prev
                light = npm(board, "light")

                # Endgame entry is checked on *every* ply, not just my moves —
                # outcomes.py has this outside its mover branch, and the
                # endgame is often entered by the opponent's move. Scoping it
                # to own moves detects entry a ply late and shifts games
                # between eval buckets.
                if eg_cp is None and fm > 12 and light <= 14:
                    eg_cp, eg_ply = cp_before, ply

                if mover == me:
                    if fm > 12 and light > 14:
                        peak = max(peak, cp_before)
                        trough = min(trough, cp_before)
                        n_elig += 1

                    cp_after = (ev if me == chess.WHITE else -ev) if ev is not None else cp_before
                    mate = abs(cp_before) >= MATE_CP or abs(cp_after) >= MATE_CP
                    see_st = standing_threat(board)
                    after_b = board.copy(stack=False)
                    after_b.push(move)
                    see_af, _ = threat_after(board, move, after_b)
                    if see_af >= 150:
                        lbl = "missed_their_threat" if see_st >= 150 else "hung_it_myself"
                    else:
                        lbl = "none"
                    legal = list(board.legal_moves)
                    nb = board.copy(stack=False)
                    nb.push(chess.Move.null())
                    my_king = board.king(board.turn)
                    n_opp_caps = sum(1 for m in nb.legal_moves
                                     if nb.is_capture(m) and m.to_square != my_king)
                    spend = (round(prev_own_clk - clk + inc, 1)
                             if (clk is not None and prev_own_clk is not None) else "")

                    op = pending_opp or {}
                    game_rows.append({
                        "block": label, "site": site, "user": user, "gid": gid,
                        "ply": ply, "fullmove": fm,
                        "side": "white" if me == chess.WHITE else "black",
                        "tc": tc, "date": date, "my_elo": my_elo, "opp_elo": opp_elo,
                        "cp_before": cp_before, "cp_after": cp_after,
                        "drop_cp": cp_before - cp_after,
                        "wp_before": round(winprob(cp_before), 6),
                        "wp_after": round(winprob(cp_after), 6),
                        "wp_error": round(winprob(cp_before) - winprob(cp_after), 6),
                        "mate_flag": int(mate),
                        "clk": clk if clk is not None else "",
                        "opp_clk": prev_opp_clk if prev_opp_clk is not None else "",
                        "spend": spend,
                        "clk_diff": (round(clk - prev_opp_clk, 1)
                                     if (clk is not None and prev_opp_clk is not None) else ""),
                        "npm_light": light, "npm_std": npm(board, "std"),
                        "mat_bal": mat_balance(board, me),
                        "queens_on": int(bool(board.pieces(chess.QUEEN, chess.WHITE))
                                         and bool(board.pieces(chess.QUEEN, chess.BLACK))),
                        "is_endgame": int(light <= 14),
                        "elig_P": int(fm > 12 and light > 14 and cp_before >= 150),
                        "see_standing": see_st, "see_after": see_af,
                        "hang_label": lbl, "in_check": int(board.is_check()),
                        "n_legal": len(legal),
                        "n_checks_avail": sum(1 for m in legal if board.gives_check(m)),
                        "n_caps_avail": sum(1 for m in legal if board.is_capture(m)),
                        "n_opp_caps": n_opp_caps,
                        "king_attackers": king_attackers(board, me),
                        "opp_prev_san": op.get("san", ""),
                        "opp_prev_kind": op.get("kind", ""),
                        "opp_created_threat": (
                            "" if (prev_own_see_after is None or not pending_opp)
                            else int(see_st >= 150 and prev_own_see_after < 150)),
                        "opp_prev_was_recapture": op.get("recap", ""),
                        "opp_prev_spend": op.get("spend", ""),
                    })
                    prev_own_clk = clk if clk is not None else prev_own_clk
                    prev_own_see_after = see_af
                    prev_own_to = move.to_square
                    pending_opp = None

                    # FENs are emitted here rather than by a later re-walk: the
                    # board is already in hand, so it costs nothing, and the
                    # position is guaranteed to be the one the row describes.
                    if fen_sel is not None:
                        row = game_rows[-1]
                        if (fen_sel == "all"
                                or (fen_sel == "elig_P" and row["elig_P"])
                                or (fen_sel == "standing_threat"
                                    and row["elig_P"] and see_st >= 150)):
                            fens.append({"gid": gid, "ply": ply, "block": label,
                                         "fen": board.fen()})
                else:
                    pending_opp = {
                        "san": board.san(move),
                        "kind": opp_move_kind(board, move),
                        "recap": int(board.is_capture(move)
                                     and prev_own_to is not None
                                     and move.to_square == prev_own_to),
                        "spend": (round(prev_opp_clk - clk + inc, 1)
                                  if (clk is not None and prev_opp_clk is not None) else ""),
                    }
                    prev_opp_clk = clk if clk is not None else prev_opp_clk

                board.push(move)
                prev = ev if ev is not None else prev
                last_cp = prev if me == chess.WHITE else -prev

            bucket = ("reached" if peak >= 200 else
                      "no_eligible" if n_elig == 0 else
                      "even" if trough > -200 else
                      "losing" if trough > -500 else "lost")
            mrows.extend(game_rows)
            grows.append({
                "gid": gid, "block": label, "site": site, "user": user, "tc": tc,
                "date": date, "color": "white" if me == chess.WHITE else "black",
                "my_elo": my_elo, "opp_elo": opp_elo, "result": res, "score": score,
                "termination": term, "is_flag": int(is_flag(term)),
                "n_plies": ply, "n_own_moves": len(game_rows), "n_elig": n_elig,
                "peak": peak if peak > -10 ** 9 else "",
                "trough": trough if trough < 10 ** 9 else "",
                "eg_entry_cp": eg_cp if eg_cp is not None else "",
                "eg_entry_ply": eg_ply if eg_ply is not None else "",
                "final_cp": last_cp,
                "opening": game.headers.get("Opening", ""),
                "eco": game.headers.get("ECO", ""),
                "bucket": bucket,
            })
    return mrows, grows, fens, st, plies_total, plies_evald, dates


def main(argv):
    tcs, blocks, umap, fen_sel = None, [], {}, None
    out = "/home/claude/features"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--tc":
            tcs = set(argv[i + 1].split(",")); i += 2; continue
        if a == "--emit-fens":
            fen_sel = argv[i + 1]
            if fen_sel not in ("all", "elig_P", "standing_threat"):
                sys.exit("--emit-fens takes: all | elig_P | standing_threat")
            i += 2; continue
        if a == "--out":
            out = argv[i + 1]; i += 2; continue
        if a == "--user-map":
            i += 1
            while i < len(argv) and not argv[i].startswith("--") and "=" in argv[i]:
                lab, who = argv[i].split("=", 1); umap[lab] = who; i += 1
            continue
        if "=" not in a:
            sys.exit(f"expected LABEL=path, got {a!r}")
        lab, path = a.split("=", 1)
        blocks.append((lab, path)); i += 1
    if not blocks:
        sys.exit(__doc__)
    os.makedirs(out, exist_ok=True)

    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=os.path.dirname(os.path.abspath(__file__)),
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = ""

    all_m, all_g, all_f, manifest = [], [], [], []
    for lab, path in blocks:
        user = umap.get(lab, USER)
        m, g, f, st, pt, pe, dates = scan(path, lab, user, tcs, fen_sel)

        # Guardrail 1 — the CHESS_USER silent zero.
        if st["games"] and not st["matched"] and not st["dropped_tc"]:
            sys.exit(f"ERROR [{lab}]: {st['games']} games read, none with user "
                     f"{user!r}. Set --user-map {lab}=<username>. Refusing to "
                     f"emit an empty block.")
        # Guardrail 2 — a _raw file fed in by mistake.
        if pt and pe / pt < 1.0:
            sys.exit(f"ERROR [{lab}]: eval coverage {pe}/{pt} "
                     f"({100*pe/pt:.1f}%) — this looks like a _raw file. "
                     f"features.py requires a fully annotated block.")
        all_m.extend(m); all_g.extend(g); all_f.extend(f)
        manifest.append({
            "block": lab, "path": os.path.abspath(path), "user": user,
            "games_read": st["games"], "matched": st["matched"],
            "dropped_user": st["dropped_user"], "dropped_tc": st["dropped_tc"],
            "plies": pt, "eval_coverage": f"{pe}/{pt}",
            "date_min": min(dates) if dates else "", "date_max": max(dates) if dates else "",
            "own_move_rows": len(m),
        })
        print(f"{lab:12} games {st['matched']:5d}/{st['games']:5d}  "
              f"rows {len(m):7d}  {min(dates) if dates else '?'} -> "
              f"{max(dates) if dates else '?'}")

    # Guardrail 3 — the chess.com free-text Termination failure.
    if all_g and not any(r["is_flag"] for r in all_g):
        sys.exit("ERROR: zero flag games across all blocks. is_flag() is not "
                 "matching this Termination format. Refusing to emit.")
    # Guardrail 4 — key integrity.
    keys = Counter((r["gid"], r["ply"]) for r in all_m)
    dup = [k for k, v in keys.items() if v > 1]
    if dup:
        sys.exit(f"ERROR: {len(dup)} duplicate (gid, ply) keys, e.g. {dup[:3]}")
    gblocks = {}
    for r in all_g:
        gblocks.setdefault(r["gid"], set()).add(r["block"])
    cross = {g: sorted(b) for g, b in gblocks.items() if len(b) > 1}
    if cross:
        print(f"WARNING: {len(cross)} gids appear in >1 block, "
              f"e.g. {list(cross.items())[:2]}", file=sys.stderr)

    with gzip.open(os.path.join(out, "moves.csv.gz"), "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MOVE_COLS); w.writeheader(); w.writerows(all_m)
    with open(os.path.join(out, "games.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=GAME_COLS); w.writeheader(); w.writerows(all_g)
    if fen_sel is not None:
        with gzip.open(os.path.join(out, "fens.csv.gz"), "wt", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["gid", "ply", "block", "fen"])
            w.writeheader(); w.writerows(all_f)
        print(f"{len(all_f)} FENs ({fen_sel}) -> {out}/fens.csv.gz")

    json.dump({"script_sha": sha, "fen_selector": fen_sel, "tc_filter": sorted(tcs) if tcs else None,
               "blocks": manifest,
               "totals": {"games": len(all_g), "own_moves": len(all_m),
                          "flag_games": sum(r["is_flag"] for r in all_g),
                          "cross_block_gids": len(cross)}},
              open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"\n{len(all_g)} games, {len(all_m)} own-move rows -> {out}/")


if __name__ == "__main__":
    main(sys.argv[1:])
