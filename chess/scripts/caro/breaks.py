#!/usr/bin/env python3
"""caro/breaks — the pawn-break moves flagged by movetypes.py, his rate vs the
thread-9 panel's Caro-as-Black games (same variety, own moves 6-30, same SF16
depth-12 evals). Exploratory, post hoc: the moves were picked by looking at his
own error rates first, so his side of the comparison is biased upward; the
panel column is the check on whether the move is just a risky move for anyone."""
import os, sys, pickle
from collections import defaultdict
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from hanging import winprob
from analyze import panel_games

MOVES = {"advance": ["d4", "f6", "g5", "e5", "f5"], "exchange": ["e5", "f6", "f5", "Ne4", "Nf5", "Nb4", "Ng4", "d4"],
         "classical_nf6": ["g5", "h5", "b5"], "bc4": ["g5", "f5", "f6", "e5"]}


def rows_of(gs):
    out = []
    for g in gs:
        b = chess.Board(); ev = g["evals"]
        for ply, u in enumerate(g["moves"][:61]):
            m = chess.Move.from_uci(u)
            if ply % 2 == 1 and ply >= 11 and ev[ply - 1] is not None and ev[ply] is not None:
                wb = 1 - winprob(ev[ply - 1]); wa = 1 - winprob(ev[ply])
                out.append((g["var"], b.san(m).rstrip("+#"), wb - wa >= 0.15, g.get("player")))
            b.push(m)
    return out


me = [(r["var"], r["san"].rstrip("+#"), r["loss"] >= 0.15) for r in pickle.load(open("/tmp/caro_moves.pkl", "rb"))]
pa = rows_of(panel_games())
agg = lambda rs: (len(rs), sum(1 for r in rs if r[2]))
print("%-14s %-5s | %-18s | %-18s" % ("variety", "move", "his n / P1%", "panel n / P1%"))
for v, ms in MOVES.items():
    bm = agg([r for r in me if r[0] == v]); bp = agg([r for r in pa if r[0] == v])
    print("%-14s %-5s | %5d  %5.1f%% | %5d  %5.1f%%" % (v, "ALL", bm[0], 100. * bm[1] / bm[0], bp[0], 100. * bp[1] / max(1, bp[0])))
    for s in ms:
        a = agg([r for r in me if r[0] == v and r[1] == s]); p = agg([r for r in pa if r[0] == v and r[1] == s])
        print("%-14s %-5s | %5d  %5.1f%% | %5d  %5.1f%%" % ("", s, a[0], 100. * a[1] / max(1, a[0]), p[0], 100. * p[1] / max(1, p[0])))
    # share of all moves that are these pawn/knight lunges
    a = agg([r for r in me if r[0] == v and r[1] in ms]); p = agg([r for r in pa if r[0] == v and r[1] in ms])
    print("%-14s %-5s | share of his moves %.1f%%, panel %.1f%%" % ("", "freq", 100. * a[0] / bm[0], 100. * p[0] / max(1, bp[0])))
