#!/usr/bin/env python3
"""review/keys.py — where each review game turned, from the depth-16 evals.

Shared by deep.py (which looks deeper at the deciding move) and
build_study_review.py (which writes the cards).

Winning chances use the Lichess curve, 1 / (1 + exp(-0.00368208 * cp)), from
his side. Definitions (fixed before reading any card):

  OK      = winning chances >= 40%.
  last_ok = the last position in the game where he was OK.
  If he was still OK in the final position, no move lost it: key = 0
  ("the clock lost it" when the game ended on time; otherwise flagged
  `ok_at_end` for the builder to handle).
  Otherwise the deciding move (key) is the first own move from the one
  that left last_ok onward that cost >= 15 points of winning chances while
  he still had >= 15%. If none qualifies, the costliest own move from there
  on while he still had >= 10%.
  also = every other own move in the game that cost >= 20 points.
"""
import math
import chess

OK, KEYDROP, ALSODROP = 0.40, 0.15, 0.20


def wp(cp_white, me_white):
    cp = cp_white if me_white else -cp_white
    cp = max(-2000, min(2000, cp))
    return 1.0 / (1.0 + math.exp(-0.00368208 * cp))


def fen4(b):
    return " ".join(b.fen().split()[:4])


def boards(g):
    b = chess.Board()
    out = [b.copy()]
    for u in g["moves"]:
        b.push_uci(u)
        out.append(b.copy())
    return out


def analyse(g, cache):
    me_white = g["me"] == "w"
    B = boards(g)
    cps = [cache[fen4(b)]["d16"] for b in B]
    W = [wp(c, me_white) for c in cps]
    n = len(g["moves"])
    mine = [j for j in range(1, n + 1) if (B[j - 1].turn == chess.WHITE) == me_white]
    drop = {j: W[j - 1] - W[j] for j in mine}
    last_ok = max(i for i in range(n + 1) if W[i] >= OK) if any(w >= OK for w in W) else 0
    res = {"W": W, "cps": cps, "mine": mine, "drop": drop, "last_ok": last_ok, "n": n}
    if last_ok == n:
        res["key"] = 0
        res["ok_at_end"] = True
    else:
        later = [j for j in mine if j > last_ok]
        cand = [j for j in later if drop[j] >= KEYDROP and W[j - 1] >= 0.15]
        if cand:
            res["key"] = cand[0]
        else:
            pool = [j for j in later if W[j - 1] >= 0.10] or later
            res["key"] = max(pool, key=lambda j: drop[j])
    res["also"] = [j for j in mine if drop[j] >= ALSODROP and j != res["key"]]
    res["peak"] = max(range(n + 1), key=lambda i: W[i])
    return res
