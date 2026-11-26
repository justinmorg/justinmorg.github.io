#!/usr/bin/env python3
"""caro/setups — within each variety, how he does against each White set-up
(score, own win chance after own moves 12 and 20, P1 per 100 own moves 6-30).
Exploratory, 2026-11-26."""
import os, sys, pickle
from collections import defaultdict
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from classify import caro_games


def has(s, mv, upto=24, white=True):
    seq = s[:upto]
    return any(x.rstrip("+") == mv for i, x in enumerate(seq) if (i % 2 == 0) == white)


def setup(g):
    s = g["sans16"]; v = g["var"]
    full = g["full"]
    if v == "advance":
        w4 = s[6] if len(s) > 6 else ""
        tag = {"c3": "4.c3", "Nf3": "4.Nf3", "dxc5": "4.dxc5", "Bb5+": "4.Bb5+", "Nc3": "4.Nc3"}.get(w4, "4.other")
        if s[2] != "d4":
            tag = "no d4 (2.%s)" % s[2]
        if has(full, "g4") or has(full, "h4"):
            tag += " +g4/h4"
        return tag
    if v in ("exchange", "nf3_exch"):
        if has(full, "c4", 20):
            return "c4 later"
        bits = []
        if has(full, "Bd3", 16): bits.append("Bd3")
        if has(full, "Bb5", 16) or has(full, "Bb5+", 16): bits.append("Bb5")
        if has(full, "Qb3", 20): bits.append("Qb3")
        if has(full, "Bf4", 16): bits.append("Bf4")
        if has(full, "Nc3", 12): bits.append("Nc3")
        if has(full, "c3", 12): bits.append("c3")
        return "+".join(bits) or "none"
    if v.startswith("classical"):
        return {"Nxf6+": "5.Nxf6+", "Ng5": "5.Ng5", "Ng3": "5.Ng3", "Nc3": "5.Nc3"}.get(s[8] if len(s) > 8 else "", "5.other")
    return "-"


cg = caro_games()
for g in cg:
    b = chess.Board(); full = []
    for u in g["moves"][:40]:
        m = chess.Move.from_uci(u); full.append(b.san(m)); b.push(m)
    g["full"] = full
mv = pickle.load(open("/tmp/caro_moves.pkl", "rb"))
by = defaultdict(list)
for r in mv:
    by[r["gid"]].append(r)
for v in ("advance", "exchange", "classical_nf6"):
    agg = defaultdict(lambda: [0, 0.0, [], [], 0, 0])
    for g in cg:
        if g["var"] != v and not (v == "exchange" and g["var"] == "nf3_exch"):
            continue
        t = setup(g); a = agg[t]
        a[0] += 1; a[1] += g["score"]
        for r in by[g["gid"]]:
            if r["move"] == 12: a[2].append(r["wa"])
            if r["move"] == 20: a[3].append(r["wa"])
            if r["move"] <= 30:
                a[4] += 1; a[5] += r["loss"] >= 0.15
    print("==", v)
    for t, a in sorted(agg.items(), key=lambda x: -x[1][0]):
        if a[0] < 12: continue
        m = lambda xs: "%2.0f" % (100 * sum(xs) / len(xs)) if xs else " -"
        print("  %-24s n=%4d score %3.0f%%  wp12 %s wp20 %s  P1 %.1f" % (t, a[0], 100 * a[1] / a[0], m(a[2]), m(a[3]), 100. * a[5] / max(1, a[4])))
