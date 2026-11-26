#!/usr/bin/env python3
"""caro/classify — sort Justin's Caro-Kann games (Black, 1.e4 c6) by variety.

Two labels per game:
  var     move-order family: advance, exchange, panov, classical (3.Nc3/Nd2 dxe4
          4.Nxe4, split by Black's 4th: bf5 / nf6 / nd7 / other), two_knights,
          fantasy, nf3_exch (2.Nf3 d5 3.exd5 cxd5 without d4), bc4 (2.Bc4),
          d3 (2.d3 / KIA-type), other.
  struct  pawn structure after ply 20 (or the last ply if shorter):
          'locked' (W e5 vs B d5/e6 chain), 'iqp' (an isolated d-pawn either side),
          'carlsbad' (exchange structure: W d4 c-pawn gone? / B d5, no c- and
          e-pawn tension), 'open_c6e6' (Classical: W d4, B c6+e6, no d5 pawn),
          'other'.
Used by caro/analyze.py and build_study_caro.py. Exploratory, 2026-11-26.
"""
import os, sys
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import studylib


def sans(g, n=16):
    b, out = chess.Board(), []
    for u in g["moves"][:n]:
        m = chess.Move.from_uci(u)
        out.append(b.san(m)); b.push(m)
    return out


def variety(s):
    s = s + [""] * 16
    if s[0] != "e4" or s[1] != "c6":
        return None
    w2, b2, w3, b3, w4, b4 = s[2:8]
    if b2 != "d5":
        return "other"
    first12 = s[:12]
    if w2 == "d4":
        if w3 == "e5":
            return "advance"
        if w3 == "exd5" and b3 == "cxd5":
            # Panov if White plays c4 within his first 6 moves
            return "panov" if "c4" in s[6:12:2] else "exchange"
        if w3 in ("Nc3", "Nd2") and b3 == "dxe4" and w4 == "Nxe4":
            return "classical_" + {"Bf5": "bf5", "Nf6": "nf6", "Nd7": "nd7"}.get(b4, "other")
        if w3 == "f3":
            return "fantasy"
        return "other"
    if w2 == "Nc3":
        if w3 == "Nf3":
            return "two_knights"
        if w3 == "d4" and b3 == "dxe4" and w4 == "Nxe4":
            return "classical_" + {"Bf5": "bf5", "Nf6": "nf6", "Nd7": "nd7"}.get(b4, "other")
        if w3 == "exd5" and b3 == "cxd5":
            return "exchange" if "d4" in s[6:12:2] and "c4" not in s[6:12:2] else "nf3_exch"
        return "other"
    if w2 == "Nf3":
        if w3 == "exd5" and b3 == "cxd5":
            if "d4" in s[6:12:2]:
                return "panov" if "c4" in s[6:12:2] else "exchange"
            return "nf3_exch"
        if w3 == "Nc3":
            return "two_knights"
        if w3 == "e5":
            return "advance"
        return "other"
    if w2 == "Bc4":
        return "bc4"
    if w2 == "d3":
        return "d3"
    if w2 == "c4":
        return "panov" if (w3 == "exd5" and b3 == "cxd5") else "other"
    return "other"


def struct(g, ply=20):
    b = chess.Board()
    for u in g["moves"][:ply]:
        b.push(chess.Move.from_uci(u))
    P = lambda c: b.pieces(chess.PAWN, c)
    wp, bp = P(chess.WHITE), P(chess.BLACK)
    files = lambda ps: [chess.square_file(x) for x in ps]
    wf, bf = files(wp), files(bp)
    sq = chess.parse_square
    if sq("e5") in wp and (sq("d5") in bp or sq("e6") in bp) and sq("d4") in wp | set():
        return "locked"
    if sq("e5") in wp and sq("d5") in bp:
        return "locked"
    def isolated(fl, myf):
        return fl in myf and (fl - 1) not in myf and (fl + 1) not in myf
    if isolated(3, wf) and 2 not in bf or isolated(3, bf) and 2 not in wf:
        return "iqp"
    if any(x in wp for x in (sq("d4"),)) and sq("d5") in bp and 4 not in wf and 2 not in bf:
        return "carlsbad"
    if sq("d4") in wp and 3 not in bf and sq("c6") in bp and (sq("e6") in bp or sq("e7") in bp):
        return "open_c6e6"
    return "other"


def caro_games(games=None):
    games = games if games is not None else studylib.load()
    out = []
    for g in games:
        if g["me"] != chess.BLACK:
            continue
        s = sans(g)
        v = variety(s)
        if v is None:
            continue
        out.append(dict(g, var=v, struct=struct(g), sans16=s))
    return out


if __name__ == "__main__":
    from collections import Counter, defaultdict
    cg = caro_games()
    print(len(cg), "Caro games")
    c = Counter(g["var"] for g in cg)
    sc = defaultdict(float)
    for g in cg:
        sc[g["var"]] += g["score"]
    for v, n in c.most_common():
        print("%-18s %5d  %4.0f%%" % (v, n, 100 * sc[v] / n))
    print(Counter((g["var"], g["struct"]) for g in cg).most_common(40))
