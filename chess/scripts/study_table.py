#!/usr/bin/env python3
"""study_table — per-own-move scan table over the corpus (cache; selection only).

One row per own move from own move 10 on. Engine-free columns come from
scanlib; the two eval columns are the depth-12 PGN evals and are used only to
select or refuse positions, never as a verdict shown on a card.
"""
import os, sys, pickle
from multiprocessing import Pool
import chess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studylib, scanlib
from hanging import SEE_VAL

CACHE = os.environ.get("STUDY_TABLE", "/tmp/study_table.pkl")
NPV = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def npm(b):
    return sum(v * len(b.pieces(pt, c)) for pt, v in NPV.items() for c in (True, False))


def rows_for(g):
    out = []
    b = chess.Board()
    me = g["me"]
    mv = [chess.Move.from_uci(u) for u in g["moves"]]
    for ply, m in enumerate(mv):
        if b.turn == me and b.fullmove_number >= 10:
            before = b.copy(stack=False)
            v = scanlib.view(before, not me, force=True)
            stale = scanlib.winning_captures(v) if v is not None else []
            d = scanlib.delta(before, m)
            nxt = mv[ply + 1] if ply + 1 < len(mv) else None
            hang_sq = [h["move"].to_square for h in d["hangs"]]
            took = nxt is not None and d["after"].is_capture(nxt) and nxt.to_square in hang_sq
            took_why = None
            if took:
                took_why = [h["why"] for h in d["hangs"] if h["move"].to_square == nxt.to_square][0]
            ev_b = studylib.my_pov(g["evals"][ply - 1], me) if ply > 0 else 0
            ev_a = studylib.my_pov(g["evals"][ply], me)
            out.append({"gid": g["gid"], "ply": ply, "fen": before.fen(), "move": m.uci(),
                        "san": before.san(m), "fm": before.fullmove_number, "me": me,
                        "check": before.is_check(), "npm": npm(before),
                        "stale": [(c["move"].uci(), c["see"], c["cls"]) for c in stale],
                        "hangs": [(h["move"].uci(), h["see"], h["cls"], h["why"]) for h in d["hangs"]],
                        "lands": [(c["move"].uci(), c["see"]) for c in d["lands"]],
                        "took": took, "took_why": took_why,
                        "nxt": nxt.uci() if nxt else None,
                        "ev_b": ev_b, "ev_a": ev_a, "last": mv[ply - 1].uci() if ply else None,
                        "block": g["block"], "date": g["date"], "opening": g["opening"], "tc": g["tc"]})
        b.push(m)
    return out


def load(refresh=False):
    if not refresh and os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    games = studylib.load()
    with Pool(2) as p:
        chunks = p.map(rows_for, games, chunksize=50)
    rows = [r for c in chunks for r in c]
    pickle.dump(rows, open(CACHE, "wb"))
    return rows


if __name__ == "__main__":
    rows = load(refresh=True)
    from collections import Counter
    print(len(rows), "own moves")
    first = Counter()
    seen = set()
    for r in rows:
        if r["took"] and (r["gid"], ) not in seen:
            first[r["took_why"]] += 1
    print("taken hangs by cause:", first)
