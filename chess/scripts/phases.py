#!/usr/bin/env python3
"""
phases.py — a phase map of the corpus: which phase each game ended in, and the
eval/clock state on entry to the middlegame and to the endgame.

Usage:
    python3 phases.py LABEL=block.pgn [LABEL=block.pgn ...] \
        [--tc 180+2,300+0] [--user-map LABEL=user ...] \
        [--clock-band 0.10] [--eval-band 100] [--out DIR]

Answers "how are games lost, at 30,000 feet": the score rate and the share of
all losses attributable to each phase, to each entry state, and to each
permutation of the two.

Definitions are imported from hanging.py and outcomes.py rather than restated,
so every figure here agrees with longitudinal.py / outcomes.py / features.py by
construction:

    middlegame entry = first position with fullmove > 12 and light npm > 14
    endgame entry    = first position with fullmove > 12 and light npm <= 14

Both detections run on EVERY ply, not just own moves. Scoping endgame entry to
own moves detects entry one ply late and silently shifts ~50 games between
buckets — see the endgame-entry ply bug in the README.

Phase the game ended in:
    opening    — no position with fullmove > 12 ever occurred
    middlegame — reached move 13, never reached light npm <= 14
    endgame    — an endgame entry occurred

Eval is centipawns from the player's POV at the entry position (the eval of the
last annotated ply before it), same convention as outcomes.py::scan.

CLOCK IS A RATIO, AND FORMATS ARE POOLED ON PURPOSE. State is own clock against
the opponent's *in the same game*, banded at +-`--clock-band` (default 10%).
This is a deliberate exception to the README's rule about splitting
clock-dependent findings past move ~25 by TimeControl. That rule protects
against comparing *absolute* late clocks across formats — 3+2 floors at ~18-20s
via the increment, 5+0 has no floor. A ratio never does that: it compares each
player only to their opponent, on the same budget. Verified monotone at every
band from 0.05 to 0.25 and in both formats separately; see the README.

Outputs (to --out, default the current directory):
    phases.csv       one row per game
    permutations.csv one row per occupied (phase, mg state, eg state) cell

GUARDRAIL: exits non-zero if a block yields games but none matching its user
(the CHESS_USER silent zero), and prints the published endgame-entry table
alongside the computed one so a run can be checked against a known number
before it is trusted.
"""
import csv
import os
import random
import re
import statistics as st
import sys
from collections import defaultdict

import chess
import chess.pgn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import USER, npm, parse_eval  # noqa: E402
from outcomes import bucket_of, is_flag  # noqa: E402

random.seed(1729)
CLK_RE = re.compile(r"\[%clk\s+([0-9:.]+)\]")

# outcomes.py's endgame-entry table, for the self-check. (games, score%)
# Valid only at the scope it was published at: seven blocks, 3+2 and 5+0.
PUBLISHED_N = 5404
PUBLISHED_EG = {"winning (>+300)": (1073, 79.4), "ahead (+100..+300)": (401, 53.2),
                "level (-100..+100)": (774, 42.7), "losing (<-100)": (1443, 19.1)}


def parse_clk(comment):
    """-> seconds remaining, or None. Handles chess.com's tenths."""
    m = CLK_RE.search(comment or "")
    if not m:
        return None
    s = 0.0
    for p in m.group(1).split(":"):
        s = s * 60 + float(p)
    return s


def base_seconds(tc):
    try:
        return float(tc.split("+")[0])
    except Exception:
        return None


def boot(vals, B=4000):
    s = sorted(st.mean(random.choices(vals, k=len(vals))) for _ in range(B))
    return st.mean(vals), s[int(.025 * B)], s[int(.975 * B)]


def scan(path, label, user, tcs):
    """One pass. Entry definitions mirror outcomes.py::scan."""
    out, n_read, n_matched = [], 0, 0
    with open(path) as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            n_read += 1
            h = game.headers
            me = (chess.WHITE if user == h.get("White", "") else
                  chess.BLACK if user == h.get("Black", "") else None)
            if me is None:
                continue
            tc = h.get("TimeControl", "")
            if tcs and tc not in tcs:
                continue
            n_matched += 1

            res = h.get("Result")
            score = 0.5 if res == "1/2-1/2" else (
                1.0 if (res == "1-0") == (me == chess.WHITE) else 0.0)

            base = base_seconds(tc)
            clk = {chess.WHITE: base, chess.BLACK: base}
            board, prev, node = game.board(), 0, game
            mg = eg = None
            reached_mg_window = False
            last_fm = board.fullmove_number

            while node.variations:
                node = node.variations[0]
                mover, fm = board.turn, board.fullmove_number
                last_fm = fm
                cp_me = prev if me == chess.WHITE else -prev
                light = npm(board, "light")
                if fm > 12:
                    reached_mg_window = True
                    if light > 14 and mg is None and eg is None:
                        mg = (cp_me, clk[me], clk[not me])
                    if light <= 14 and eg is None:
                        eg = (cp_me, clk[me], clk[not me])
                ev = parse_eval(node.comment, mover == chess.WHITE)
                c = parse_clk(node.comment)
                board.push(node.move)
                if ev is not None:
                    prev = ev
                if c is not None:
                    clk[mover] = c

            out.append(dict(
                block=label, gid=h.get("GameId", ""), tc=tc, user=user,
                result=res, score=score,
                phase=("endgame" if eg else "middlegame" if reached_mg_window
                       else "opening"),
                last_fullmove=last_fm, termination=h.get("Termination", ""),
                mg_cp="" if mg is None else round(mg[0]),
                mg_myclk="" if mg is None else round(mg[1], 1),
                mg_oppclk="" if mg is None else round(mg[2], 1),
                eg_cp="" if eg is None else round(eg[0]),
                eg_myclk="" if eg is None else round(eg[1], 1),
                eg_oppclk="" if eg is None else round(eg[2], 1)))
    return out, n_read, n_matched


def states(rows, eval_band, clock_band):
    """Attach (eval_state, clock_state) tuples for each entry point."""
    import math
    t = math.log(1 + clock_band)

    def ev(cp):
        cp = int(cp)
        return "up" if cp > eval_band else ("down" if cp <= -eval_band else "even")

    def cl(mine, opp):
        r = math.log(max(float(mine), .1) / max(float(opp), .1))
        return "up" if r > t else ("down" if r < -t else "even")

    for r in rows:
        for pre in ("mg", "eg"):
            r[pre] = (None if r[pre + "_cp"] == "" else
                      (ev(r[pre + "_cp"]), cl(r[pre + "_myclk"], r[pre + "_oppclk"])))


def grid(rows, pre, N, L, title):
    sub = [r for r in rows if r[pre]]
    print(f"\n{title}  (n={len(sub)})")
    hdr = "".join(f"{'clock ' + c:>18}" for c in ("up", "even", "down"))
    print(f"  {'eval \\ clock':14}{hdr}{'row':>18}")
    for e in ("up", "even", "down"):
        line = f"  {e:14}"
        for c in ("up", "even", "down"):
            v = [r["score"] for r in sub if r[pre] == (e, c)]
            line += (f"{len(v):8}{100 * sum(v) / len(v):8.1f}%" if v else f"{'-':>18}")
        v = [r["score"] for r in sub if r[pre][0] == e]
        line += f"{len(v):8}{100 * sum(v) / len(v):8.1f}%"
        print(line)
    line = f"  {'col':14}"
    for c in ("up", "even", "down"):
        v = [r["score"] for r in sub if r[pre][1] == c]
        line += f"{len(v):8}{100 * sum(v) / len(v):8.1f}%"
    print(line)

    g = defaultdict(list)
    for r in sub:
        g[f"eval {r[pre][0]}, clock {r[pre][1]}"].append(r["score"])
    print(f"  {'cell':26}{'games':>7}{'%games':>8}{'score':>8}"
          f"{'losses':>8}{'%all L':>8}")
    for k in sorted(g, key=lambda k: -sum(1 for s in g[k] if s == 0)):
        v = g[k]
        ls = sum(1 for s in v if s == 0)
        print(f"  {k:26}{len(v):7}{100 * len(v) / N:7.1f}%{100 * sum(v) / len(v):7.1f}%"
              f"{ls:8}{100 * ls / L:7.1f}%")


def main(argv):
    tcs, blocks, umap = None, [], {}
    eval_band, clock_band, outdir = 100, 0.10, "."
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--tc":
            tcs = set(argv[i + 1].split(",")); i += 2; continue
        if a == "--eval-band":
            eval_band = int(argv[i + 1]); i += 2; continue
        if a == "--clock-band":
            clock_band = float(argv[i + 1]); i += 2; continue
        if a == "--out":
            outdir = argv[i + 1]; i += 2; continue
        if a == "--user-map":
            i += 1
            while i < len(argv) and "=" in argv[i] and not argv[i].startswith("--"):
                lab, who = argv[i].split("=", 1)
                umap[lab] = who
                i += 1
            continue
        if "=" not in a:
            sys.exit(f"expected LABEL=path, got {a!r}")
        lab, path = a.split("=", 1)
        blocks.append((lab, path)); i += 1
    if not blocks:
        sys.exit(__doc__)

    os.makedirs(outdir, exist_ok=True)
    rows = []
    print(f"default user: {USER}   time controls: {sorted(tcs) if tcs else 'ALL'}")
    print(f"eval band: +-{eval_band}cp   clock band: +-{clock_band:.0%} (ratio, "
          f"formats pooled)\n")
    for lab, path in blocks:
        user = umap.get(lab, USER)
        got, r, m = scan(path, lab, user, tcs)
        if r and not m:
            sys.exit(f"FATAL: {lab}: {r} games read, 0 matched user {user!r}. "
                     f"Set --user-map or CHESS_USER.")
        print(f"  {lab:12} user={user:11} read={r:5}  matched={m:5}")
        rows += got

    states(rows, eval_band, clock_band)
    N = len(rows)
    L = sum(1 for r in rows if r["score"] == 0)
    W = sum(1 for r in rows if r["score"] == 1)
    D = sum(1 for r in rows if r["score"] == .5)
    m, lo, hi = boot([r["score"] for r in rows])
    print(f"\n{N} games   {W}W / {D}D / {L}L   "
          f"score {100 * m:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]")

    # ---- self-check against outcomes.py's published endgame-entry table.
    # Only meaningful at the scope those figures were published at: all seven
    # annotated blocks, 3+2 and 5+0. On any narrower run the counts differ by
    # construction, so assert nothing rather than report a false MISMATCH.
    g = defaultdict(list)
    for r in rows:
        if r["eg_cp"] != "":
            g[bucket_of(int(r["eg_cp"]))].append(r["score"])
    if N == PUBLISHED_N:
        print("\nSELF-CHECK — endgame-entry buckets vs the README "
              "(mismatch means a bug here, not a finding):")
        ok = True
        for k, (pn, ps) in PUBLISHED_EG.items():
            v = g[k]
            sc = 100 * sum(v) / len(v) if v else 0
            match = (len(v) == pn and abs(sc - ps) < 0.05)
            ok &= match
            print(f"  {k:22}{len(v):6} {sc:5.1f}%   published {pn:5} {ps:5.1f}%  "
                  f"{'ok' if match else 'MISMATCH'}")
        if not ok:
            sys.exit("  DOES NOT REPRODUCE the published endgame-entry table — "
                     "this is a bug here, not a finding. Refusing to emit tables.")
        print("  all buckets reproduce")
    else:
        print(f"\nSELF-CHECK skipped: {N} games, not the {PUBLISHED_N} of the "
              f"seven-block 3+2/5+0 scope the published figures use. Run the "
              f"full scope to validate the pipeline.")

    # ---- 1. phase
    print(f"\nPHASE THE GAME ENDED IN")
    print(f"  {'phase':26}{'games':>7}{'%games':>8}{'score':>8}{'losses':>8}{'%all L':>8}")
    for ph in ("opening", "middlegame", "endgame"):
        v = [r["score"] for r in rows if r["phase"] == ph]
        ls = sum(1 for s in v if s == 0)
        print(f"  {ph:26}{len(v):7}{100 * len(v) / N:7.1f}%{100 * sum(v) / len(v):7.1f}%"
              f"{ls:8}{100 * ls / L:7.1f}%")
    nomg = sum(1 for r in rows if not r["mg"])
    print(f"  ({nomg} games have no middlegame entry: ended in the opening, or "
          f"simplified below npm>14 before move 13)")

    grid(rows, "mg", N, L, "STATE ENTERING THE MIDDLEGAME")
    grid(rows, "eg", N, L, "STATE ENTERING THE ENDGAME")

    # ---- eval transition
    both = [r for r in rows if r["mg"] and r["eg"]]
    print(f"\nEVAL TRANSITION, MIDDLEGAME ENTRY -> ENDGAME ENTRY (n={len(both)})")
    print(f"  {'mg eval':10}" + "".join(f"{'eg ' + c:>22}" for c in ("up", "even", "down")))
    for e in ("up", "even", "down"):
        line = f"  {e:10}"
        for c in ("up", "even", "down"):
            v = [r["score"] for r in both if r["mg"][0] == e and r["eg"][0] == c]
            ls = sum(1 for s in v if s == 0)
            line += (f"{len(v):7}{100 * sum(v) / len(v):6.1f}% L{100 * ls / L:5.1f}%"
                     if v else f"{'-':>22}")
        print(line)

    # ---- flags, so the clock columns are not read as forfeits
    fl = sum(1 for r in rows if r["score"] == 0 and is_flag(r["termination"]))
    print(f"\nflag losses: {fl} of {L} losses = {100 * fl / L:.1f}%")
    for c in ("up", "even", "down"):
        sub = [r for r in rows if r["score"] == 0 and r["eg"] and r["eg"][1] == c]
        f = sum(1 for r in sub if is_flag(r["termination"]))
        print(f"  EG entry clock {c:5}: {len(sub):5} losses, {f:4} flags "
              f"= {100 * f / max(1, len(sub)):.1f}%")

    # ---- write
    gp = os.path.join(outdir, "phases.csv")
    with open(gp, "w", newline="") as fh:
        cols = ["block", "gid", "tc", "user", "result", "score", "phase",
                "last_fullmove", "termination", "mg_cp", "mg_myclk", "mg_oppclk",
                "eg_cp", "eg_myclk", "eg_oppclk"]
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    cells = defaultdict(list)
    for r in rows:
        cells[(r["phase"],
               r["mg"][0] if r["mg"] else "", r["mg"][1] if r["mg"] else "",
               r["eg"][0] if r["eg"] else "", r["eg"][1] if r["eg"] else "")
              ].append(r["score"])
    pp = os.path.join(outdir, "permutations.csv")
    with open(pp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["phase_ended", "mg_eval", "mg_clock", "eg_eval", "eg_clock",
                    "games", "pct_of_games", "wins", "draws", "losses",
                    "score_pct", "pct_of_all_losses"])
        for k in sorted(cells, key=lambda k: -sum(1 for s in cells[k] if s == 0)):
            v = cells[k]
            ls = sum(1 for s in v if s == 0)
            w.writerow(list(k) + [len(v), round(100 * len(v) / N, 2),
                                  sum(1 for s in v if s == 1),
                                  sum(1 for s in v if s == .5), ls,
                                  round(100 * sum(v) / len(v), 1),
                                  round(100 * ls / L, 2)])
    print(f"\n{len(cells)} occupied permutation cells -> {pp}\nper-game table -> {gp}")


if __name__ == "__main__":
    main(sys.argv[1:])
