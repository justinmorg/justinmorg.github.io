#!/usr/bin/env python3
"""trades/extract — one row per "trade decision" from a materially level position,
both sides' moves (2026-11-25, exploratory, not pre-registered).

Parked idea 3 ("trades from materially level positions"). A decision point is a
position where:
  * the side to move is not in check,
  * material is within one pawn of level (P1 N3 B3 R5 Q9; column `bal` is the
    mover-POV balance, -1/0/+1 — "level" in the analysis means bal == 0; the
    +/-1 rows exist only to widen the thin low-clock cells),
  * the mover has at least one EVEN PIECE TRADE available: a capture of an N/B/R/Q
    by a piece of the same value class (N and B are one class), on a square the
    opponent can recapture on, with static exchange value exactly 0 (hanging.see).
took = the move played is one of those captures. Declined = anything else.

Scope: studylib corpus (Lichess, 3+2 / 5+0), the plateau blocks (2024h2,
2025q1-q4, 2026, pending) and the F block (2026_fblock), as in egtruth.

    python3 extract.py OUT.csv.gz

Columns (all from the MOVER's POV):
  gid block era tc mine bal trade_pc (e.g. BxN: capturer x captured, if took) fen san fam caro fullmove phase npm_light men n_avail took
  trade_type (piece class captured if took, else '')  avail_types ('Q|R|M' set)
  cp_before cp_after wp_before wp_after wp_err   (depth-12, Lichess curve)
  clock_before opp_clock spent
  f_moves f_e10 f_e20 f_wpl  (next 10 own moves after this one: count observed,
                              errors >= 0.10 / >= 0.20 win-prob, summed wp lost)
  wp_p20  (mover's win prob 20 plies later, '' if game ended)
  score   (final result from the mover's side)
"""
import os, sys, csv, gzip
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import studylib
from hanging import see, winprob, MATE_CP
from studydose import family, caro_line

PLATEAU = {"2024h2", "2025q1", "2025q2", "2025q3", "2025q4", "2026", "pending"}
TREAT = {"2026_fblock"}
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
CLS = {chess.KNIGHT: "M", chess.BISHOP: "M", chess.ROOK: "R", chess.QUEEN: "Q"}
LIGHT = {chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4}


def material(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)


def npm_light(b):
    return sum(LIGHT.get(p.piece_type, 0) for p in b.piece_map().values())


def even_trades(b):
    out = []
    for m in b.legal_moves:
        if not b.is_capture(m) or b.is_en_passant(m) or m.promotion:
            continue
        a, v = b.piece_type_at(m.from_square), b.piece_type_at(m.to_square)
        if a not in CLS or v not in CLS or CLS[a] != CLS[v]:
            continue
        if see(b, m) != 0:
            continue
        b.push(m)
        recap = any(r.to_square == m.to_square for r in b.legal_moves if b.is_capture(r))
        b.pop()
        if recap:
            out.append((m, CLS[v]))
    return out


def phase(b, fullmove):
    n = npm_light(b)
    if fullmove <= 12:
        return "opening"
    return "middlegame" if n > 14 else "endgame"


def wpov(cp, white):
    if cp is None:
        return None
    return cp if white else -cp


def main(out):
    games = studylib.load()
    cols = ["gid", "block", "era", "tc", "mine", "bal", "trade_pc", "fen", "san", "fam", "caro", "fullmove", "phase", "npm_light", "men",
            "n_avail", "took", "trade_type", "avail_types", "cp_before", "cp_after", "wp_before", "wp_after",
            "wp_err", "clock_before", "opp_clock", "spent", "f_moves", "f_e10", "f_e20", "f_wpl", "wp_p20", "score"]
    n = 0
    with gzip.open(out, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for g in games:
            if g["block"] in PLATEAU:
                era = "plateau"
            elif g["block"] in TREAT:
                era = "treat"
            else:
                continue
            inc = 2 if g["tc"] == "180+2" else 0
            start = 180 if g["tc"] == "180+2" else 300
            ev, ck, mv = g["evals"], g["clocks"], g["moves"]
            b = chess.Board()
            sans = []
            for u in mv[:6]:
                m = chess.Move.from_uci(u); sans.append(b.san(m)); b.push(m)
            col = "white" if g["me"] == chess.WHITE else "black"
            fam = family(col, sans)
            caro = caro_line(sans) if fam == "Caro" else ""

            # per-ply mover wp before/after, to build follow-up windows
            def wp_at(ply_after, white):  # mover-POV wp after ply index ply_after (-1 = start)
                if ply_after < 0:
                    return 0.5
                c = wpov(ev[ply_after], white)
                return None if c is None else winprob(c)

            b = chess.Board()
            for ply, u in enumerate(mv):
                m = chess.Move.from_uci(u)
                mover = b.turn
                bal = material(b, mover) - material(b, not mover)
                if not b.is_check() and abs(bal) <= 1:
                    avail = even_trades(b)
                    if avail:
                        white = mover == chess.WHITE
                        mine = mover == g["me"]
                        cb = wpov(ev[ply - 1], white) if ply >= 1 else 0
                        ca = wpov(ev[ply], white)
                        if cb is not None and ca is not None and abs(cb) < MATE_CP and abs(ca) <= MATE_CP:
                            took = [t for (x, t) in avail if x == m]
                            wb, wa = winprob(cb), winprob(ca)
                            prev = ck[ply - 2] if ply >= 2 else start
                            cur = ck[ply]
                            spent = (prev - cur + inc) if (prev is not None and cur is not None) else ""
                            oc = ck[ply - 1] if ply >= 1 else start
                            # follow-up: next 10 own moves
                            fm = fe10 = fe20 = 0; fwpl = 0.0
                            for k in range(1, 11):
                                p = ply + 2 * k
                                if p >= len(mv):
                                    break
                                x0, x1 = wp_at(p - 1, white), wp_at(p, white)
                                if x0 is None or x1 is None:
                                    continue
                                e = x0 - x1
                                fm += 1; fe10 += e >= 0.10; fe20 += e >= 0.20; fwpl += max(e, 0)
                            p20 = ply + 20
                            wp20 = wp_at(p20, white) if p20 < len(mv) else None
                            sc = g["score"] if mine else 1.0 - g["score"]
                            w.writerow([g["gid"], g["block"], era, g["tc"], int(mine), bal,
                                        "NBRQ"[[chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN].index(b.piece_type_at(m.from_square))] + "x" + "NBRQ"[[chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN].index(b.piece_type_at(m.to_square))] if took else "",
                                        b.fen(), b.san(m), fam, caro, b.fullmove_number,
                                        phase(b, b.fullmove_number), npm_light(b), chess.popcount(b.occupied),
                                        len(avail), int(bool(took)), took[0] if took else "",
                                        "|".join(sorted({t for _, t in avail})), cb, ca, round(wb, 4), round(wa, 4),
                                        round(wb - wa, 4), "" if prev is None else prev, "" if oc is None else oc,
                                        spent, fm, fe10, fe20, round(fwpl, 4),
                                        "" if wp20 is None else round(wp20, 4), sc])
                            n += 1
                b.push(m)
    print(n, "rows")


if __name__ == "__main__":
    main(sys.argv[1])
