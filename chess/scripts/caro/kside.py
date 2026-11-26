#!/usr/bin/env python3
"""caro/kside — kingside pawn moves (f/g/h-pawn, Black, own moves 6-30) in his
Caro games vs the thread-9 panel's: how often, and how often a P1 error.
Exploratory and post hoc (suggested by movetypes.py / breaks.py). Also the
opponent-rating check for the Exchange c3 vs Nc3 split."""
import os, sys, random
from collections import defaultdict
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from hanging import winprob
from classify import caro_games
from analyze import panel_games
FAMS = {"advance": "Advance", "exchange": "Exchange", "nf3_exch": "Exchange", "classical_nf6": "4.Nxe4",
        "classical_bf5": "4.Nxe4", "classical_nd7": "4.Nxe4", "bc4": "2.Bc4", "panov": "Panov"}


def rows(g):
    b = chess.Board(); ev = g["evals"]; out = []
    for ply, u in enumerate(g["moves"][:61]):
        m = chess.Move.from_uci(u)
        if ply % 2 == 1 and ply >= 11 and ev[ply - 1] is not None and ev[ply] is not None:
            ks = b.piece_type_at(m.from_square) == chess.PAWN and chess.square_file(m.from_square) >= 5 and not b.is_capture(m)
            out.append((ks, (1 - winprob(ev[ply - 1])) - (1 - winprob(ev[ply])) >= 0.15))
        b.push(m)
    return out


def summ(gs):
    per = [rows(g) for g in gs]
    def stat(sample):
        k = [x for r in sample for x in r if x[0]]; o = [x for r in sample for x in r if not x[0]]
        n = len(k) + len(o)
        return 100. * len(k) / max(1, n), 100. * sum(x[1] for x in k) / max(1, len(k)), 100. * sum(x[1] for x in o) / max(1, len(o)), len(k)
    s = stat(per)
    rnd = random.Random(11); B = []
    for _ in range(1000):
        smp = [per[rnd.randrange(len(per))] for _ in per]
        x = stat(smp); B.append(x[1] - x[2])
    B.sort()
    return s, (B[25], B[975])


if __name__ == "__main__":
    me = caro_games(); pa = panel_games()
    print("%-9s | %-44s | %s" % ("family", "him: share / P1 kside / P1 other [diff 95%]", "panel: share / P1 kside / P1 other [diff 95%]"))
    for fam in ("Advance", "Exchange", "4.Nxe4", "2.Bc4", "ALL"):
        a = [g for g in me if FAMS.get(g["var"]) == fam or (fam == "ALL" and g["var"] in FAMS)]
        p = [g for g in pa if FAMS.get(g["var"]) == fam or (fam == "ALL" and g["var"] in FAMS)]
        (s1, c1), (s2, c2) = summ(a), (summ(p) if len(p) > 20 else ((0, 0, 0, 0), (0, 0)))
        print("%-9s | %4.1f%% %5.1f%% %4.1f%% n=%4d [%+.1f,%+.1f] | %4.1f%% %5.1f%% %4.1f%% n=%3d [%+.1f,%+.1f]" % (
            fam, s1[0], s1[1], s1[2], s1[3], c1[0], c1[1], s2[0], s2[1], s2[2], s2[3], c2[0], c2[1]))
    # opponent rating, Exchange c3 vs Nc3
    def full(g, n=24):
        b = chess.Board(); out = []
        for u in g["moves"][:n]:
            m = chess.Move.from_uci(u); out.append(b.san(m)); b.push(m)
        return out
    for t in ("c3", "Nc3"):
        gs = []
        for g in me:
            if g["var"] not in ("exchange", "nf3_exch"):
                continue
            f = full(g)
            k = "c3" if ("c3" in f[0::2] and "c4" not in f[0::2]) else ("Nc3" if "Nc3" in f[0::2] else "x")
            if k == t:
                gs.append(g)
        d = [int(g["opp_elo"]) - int(g["my_elo"]) for g in gs if g["opp_elo"] and g["my_elo"]]
        print("Exchange %s: %d games, opponent minus me %+.0f Elo on average" % (t, len(gs), sum(d) / len(d)))
