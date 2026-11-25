#!/usr/bin/env python3
"""egtruth/extract — one row per endgame ply (both sides), for the truth-check,
time-map and practice-deck work of 2026-11-25.

Scope: studylib corpus (Lichess, 3+2 / 5+0), blocks 2024h2, 2025q1-q4, 2026,
pending ("plateau") and 2026_fblock ("treat"). 2023 and 2024rest excluded
(pre-repertoire era). Endgame = build_study_endgames.is_endgame (move 13+,
npm <= 26, or queens off and npm <= 32) — the plateau-review definition.

    python3 extract.py OUT.csv.gz

Columns: gid block era tc me_white mine ply fullmove fen uci san piece
  capture check promo men etype npm passed_mover passed_other
  cp_before cp_after (mover POV, depth 12; None if missing)
  wp_before wp_after (Lichess curve)  clock_before spent opp_clock score
  (score = game result from the MOVER's side)
"""
import os, sys, csv, gzip
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import studylib
from hanging import winprob
from build_study_endgames import is_endgame, eg_type, passed_pawns, npm

PLATEAU = {"2024h2", "2025q1", "2025q2", "2025q3", "2025q4", "2026", "pending"}
TREAT = {"2026_fblock"}
PNAME = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}


def main(out):
    games = studylib.load()
    cols = ["gid", "block", "era", "tc", "me_white", "mine", "ply", "fullmove", "fen", "uci", "san", "piece",
            "capture", "check", "promo", "men", "etype", "npm", "passed_mover", "passed_other",
            "cp_before", "cp_after", "wp_before", "wp_after", "clock_before", "spent", "opp_clock", "score"]
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
            b = chess.Board()
            ev, ck = g["evals"], g["clocks"]
            for ply, u in enumerate(g["moves"]):
                m = chess.Move.from_uci(u)
                if is_endgame(b):
                    mover = b.turn
                    mine = mover == g["me"]
                    sgn = 1 if mover == chess.WHITE else -1
                    cb = ev[ply - 1] if ply >= 1 else 0
                    ca = ev[ply]
                    cb = None if cb is None else sgn * cb
                    ca = None if ca is None else sgn * ca
                    prev = ck[ply - 2] if ply >= 2 else start
                    cur = ck[ply]
                    spent = (prev - cur + inc) if (prev is not None and cur is not None) else None
                    oc = ck[ply - 1] if ply >= 1 else start
                    sc = g["score"] if mine else 1.0 - g["score"]
                    w.writerow([g["gid"], g["block"], era, g["tc"], int(g["me"] == chess.WHITE), int(mine), ply,
                                b.fullmove_number, b.fen(), u, b.san(m), PNAME[b.piece_type_at(m.from_square)],
                                int(b.is_capture(m)), int(b.gives_check(m)), int(m.promotion is not None),
                                chess.popcount(b.occupied), eg_type(b), npm(b),
                                len(passed_pawns(b, mover)), len(passed_pawns(b, not mover)),
                                cb, ca,
                                "" if cb is None else round(winprob(cb), 4),
                                "" if ca is None else round(winprob(ca), 4),
                                prev, spent, oc, sc])
                    n += 1
                b.push(m)
    print(n, "rows")


if __name__ == "__main__":
    main(sys.argv[1])
