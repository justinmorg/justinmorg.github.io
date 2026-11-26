#!/usr/bin/env python3
"""caro/movetypes — per-variety, which of his recurring moves (same SAN, own moves
6-30) carry an error rate well above his baseline in that variety. Exploratory.
Writes /tmp/caro_moves.pkl (all own-move rows) for themes.py."""
import os, sys, pickle
from collections import defaultdict
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from hanging import winprob
from classify import caro_games

rows = []
for g in caro_games():
    b = chess.Board()
    ev = g["evals"]
    for ply, u in enumerate(g["moves"][:61]):
        m = chess.Move.from_uci(u)
        if ply % 2 == 1 and ply >= 11 and ev[ply - 1] is not None and ev[ply] is not None:
            wb = 1 - winprob(ev[ply - 1]); wa = 1 - winprob(ev[ply])
            rows.append(dict(gid=g["gid"], var=g["var"], ply=ply, move=(ply + 1) // 2, san=b.san(m),
                             fen=b.fen(), uci=u, wb=wb, wa=wa, loss=wb - wa, score=g["score"],
                             clock=g["clocks"][ply], block=g["block"]))
        b.push(m)
pickle.dump(rows, open("/tmp/caro_moves.pkl", "wb"))
import pandas as pd
d = pd.DataFrame(rows)
d["p1"] = d.loss >= 0.15
d["san0"] = d.san.str.replace("+", "", regex=False).str.replace("#", "", regex=False)
for v in ["advance", "exchange", "classical_nf6", "bc4"]:
    x = d[d["var"] == v]
    base = x.p1.mean()
    t = x.groupby("san0").agg(n=("p1", "size"), p1=("p1", "mean"), loss=("loss", "mean")).query("n>=15")
    t["x"] = t.p1 / base
    print("== %s: %d moves, base P1 %.1f%%" % (v, len(x), 100 * base))
    print(t.sort_values("p1", ascending=False).head(14).round(3).to_string())
