#!/usr/bin/env python3
"""
material.py — game outcome as a function of material on the board, conditioned
on the position being roughly level at the moment that material level is first
reached.

Usage:
    python3 material.py LABEL=block.pgn [...] [--tc 180+2,300+0]
        [--user-map LABEL=user ...] [--band 100] [--out DIR]

Axis is `npm(board, "light")` — N=1, B=1, R=2, Q=4, both sides — which runs
from 24 at the starting position down to 0 at bare kings. That is the same
scale the endgame-entry threshold (<= 14) is defined on.

CONSTRUCTION. For each game and each level M in 24..0, take the FIRST position
where light npm <= M. If |eval| <= --band at that position, the game enters the
sample for M with its final result. Three consequences worth holding onto:

  * Material falls in jumps (a queen trade drops 4 at once), so one position can
    be the first crossing for several adjacent M. Adjacent points on the curve
    therefore SHARE POSITIONS and are not independent. The curve is smoother
    than the data warrants; do not read local wiggles.
  * A game only appears at level M if it survived to reach M. This is a
    survivorship filter, not a random sample, and it tightens as M falls.
  * THE BENCHMARK IS NOT 50%. This is the trap this script exists to prevent.
    A level position scores 50% only within a symmetrically selected
    population, and "reached npm M" is not one: wins end early and losses run
    long (opening 73.6%, middlegame 57.7%, endgame 45.3% -- see the phase map),
    so games reaching low material score well below 50% before eval is
    mentioned at all. The `reach` column is the correct benchmark and the
    `diff` column is the finding. Reading the `level` column against 50% turns
    a -3 point middlegame effect into a spurious -7 point flat one.

M=24 is the starting position of every game, eval 0, so that point is by
construction the overall score rate. It is a free correctness anchor: if the
left edge of the curve is not the corpus score rate, the pass is broken.

Also splits level positions by clock state (own clock vs opponent's, ratio,
+-`--clock-band`, the cut established in phases.py) and prints the symmetric
cell -- level eval AND level clock -- at tightening bands.

Outputs material.csv and prints the curve.
"""
import csv
import os
import random
import statistics as st
import sys
from collections import defaultdict

import math
import re

import chess
import chess.pgn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import USER, npm, parse_eval  # noqa: E402

random.seed(1729)
LEVELS = list(range(24, -1, -1))
CLK_RE = re.compile(r"\[%clk\s+([0-9:.]+)\]")


def parse_clk(comment):
    m = CLK_RE.search(comment or "")
    if not m:
        return None
    s = 0.0
    for p in m.group(1).split(":"):
        s = s * 60 + float(p)
    return s


def boot(vals, B=2000):
    if len(vals) < 2:
        return (st.mean(vals) if vals else 0), 0, 1
    s = sorted(st.mean(random.choices(vals, k=len(vals))) for _ in range(B))
    return st.mean(vals), s[int(.025 * B)], s[int(.975 * B)]


def scan(path, label, user, tcs, band):
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
            if tcs and h.get("TimeControl", "") not in tcs:
                continue
            n_matched += 1
            res = h.get("Result")
            score = 0.5 if res == "1/2-1/2" else (
                1.0 if (res == "1-0") == (me == chess.WHITE) else 0.0)
            tc = h.get("TimeControl", "")
            try:
                base = float(tc.split("+")[0])
            except Exception:
                base = None
            clk = {chess.WHITE: base, chess.BLACK: base}

            # first crossing of each material level -> (cp, my clock, opp clock)
            first = {}
            board, prev, node = game.board(), 0, game
            lowest = 99
            while True:
                cur = npm(board, "light")
                if cur < lowest:
                    cp_me = prev if me == chess.WHITE else -prev
                    for M in range(cur, min(lowest, 25)):
                        first[M] = (cp_me, clk[me], clk[not me])
                    lowest = cur
                if not node.variations:
                    break
                node = node.variations[0]
                mover = board.turn
                ev = parse_eval(node.comment, mover == chess.WHITE)
                c = parse_clk(node.comment)
                board.push(node.move)
                if ev is not None:
                    prev = ev
                if c is not None:
                    clk[mover] = c

            out.append(dict(gid=h.get("GameId", ""), block=label, score=score,
                            result=res, reached=first, final_npm=lowest))
    return out, n_read, n_matched


def main(argv):
    tcs, blocks, umap, band, outdir, clock_band = None, [], {}, 100, ".", 0.10
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--tc":
            tcs = set(argv[i + 1].split(",")); i += 2; continue
        if a == "--band":
            band = int(argv[i + 1]); i += 2; continue
        if a == "--clock-band":
            clock_band = float(argv[i + 1]); i += 2; continue
        if a == "--out":
            outdir = argv[i + 1]; i += 2; continue
        if a == "--user-map":
            i += 1
            while i < len(argv) and "=" in argv[i] and not argv[i].startswith("--"):
                lab, who = argv[i].split("=", 1)
                umap[lab] = who; i += 1
            continue
        lab, path = a.split("=", 1)
        blocks.append((lab, path)); i += 1
    if not blocks:
        sys.exit(__doc__)
    os.makedirs(outdir, exist_ok=True)

    games = []
    for lab, path in blocks:
        user = umap.get(lab, USER)
        got, r, m = scan(path, lab, user, tcs, band)
        if r and not m:
            sys.exit(f"FATAL: {lab}: {r} read, 0 matched {user!r}")
        print(f"  {lab:12} user={user:11} read={r:5}  matched={m:5}")
        games += got

    N = len(games)
    overall = st.mean([g["score"] for g in games])
    print(f"\n{N} games, overall score {100 * overall:.1f}%   band +-{band}cp")

    anchor = [g["score"] for g in games if 24 in g["reached"]]
    print(f"ANCHOR: level 24 holds {len(anchor)} games at "
          f"{100 * st.mean(anchor):.1f}% — must equal {N} and "
          f"{100 * overall:.1f}%  "
          f"{'ok' if len(anchor) == N and abs(st.mean(anchor) - overall) < 1e-9 else 'BROKEN'}")

    cb = clock_band
    T = math.log(1 + cb)

    def cstate(mine, opp):
        r = math.log(max(mine, .1) / max(opp, .1))
        return "up" if r > T else ("down" if r < -T else "even")

    rows = []
    print(f"\n{'npm':>4} {'reach':>6} {'%reach':>7} {'BENCHMARK':>10} | {'level n':>8} "
          f"{'level':>7} {'DIFF':>6} {'95% CI':>14} {'W':>5} {'D':>5} {'L':>5} {'draw%':>6}")
    print("  (BENCHMARK = score of every game reaching this level. DIFF is the "
          "finding; the level column alone is not.)")
    for M in LEVELS:
        reach = [g for g in games if M in g["reached"]]
        lvl = [g for g in reach if abs(g["reached"][M][0]) <= band]
        if not lvl:
            continue
        bm = st.mean([g["score"] for g in reach])
        sc = [g["score"] for g in lvl]
        m, lo, hi = boot(sc)
        w = sum(1 for x in sc if x == 1)
        d = sum(1 for x in sc if x == .5)
        ls = sum(1 for x in sc if x == 0)
        print(f"{M:4} {len(reach):6} {100 * len(reach) / N:6.1f}% {100 * bm:9.1f}% | "
              f"{len(lvl):8} {100 * m:6.1f}% {100 * (m - bm):+5.1f} "
              f"[{100 * lo:5.1f},{100 * hi:5.1f}] {w:5} {d:5} {ls:5} "
              f"{100 * d / len(lvl):5.1f}%")
        rows.append(dict(npm=M, games_reaching=len(reach),
                         pct_reaching=round(100 * len(reach) / N, 1),
                         benchmark_score_pct=round(100 * bm, 1),
                         level_n=len(lvl), score_pct=round(100 * m, 1),
                         diff_vs_benchmark=round(100 * (m - bm), 1),
                         ci_lo=round(100 * lo, 1), ci_hi=round(100 * hi, 1),
                         wins=w, draws=d, losses=ls,
                         draw_pct=round(100 * d / len(lvl), 1)))

    # ---- clock split, game-level (one observation per game) over a band of M
    lo_M, hi_M = 4, 19
    print(f"\nCLOCK STATE AT THE FIRST LEVEL CROSSING IN npm {hi_M}..{lo_M} "
          f"(one obs per game, ratio band +-{cb:.0%})")
    allg, lv = defaultdict(list), defaultdict(list)
    for g in games:
        for M in range(hi_M, lo_M - 1, -1):
            if M in g["reached"]:
                cp, mine, opp = g["reached"][M]
                c = cstate(mine, opp)
                allg[c].append(g["score"])
                if abs(cp) <= band:
                    lv[c].append(g["score"])
                break
    print(f"  {'clock':>6}{'all n':>8}{'all score':>11}{'level n':>9}{'level':>8}{'diff':>7}")
    for c in ("up", "even", "down"):
        a, l = allg[c], lv[c]
        if not a or not l:
            continue
        print(f"  {c:>6}{len(a):8}{100 * st.mean(a):10.1f}%{len(l):9}"
              f"{100 * st.mean(l):7.1f}%{100 * (st.mean(l) - st.mean(a)):+6.1f}")

    # ---- the symmetric cell: level eval AND level clock, both bands tightening
    print("\nSYMMETRIC CELL — level eval AND level clock. Under player symmetry "
          "this would be\n  the benchmark; the residual is the part the clock "
          "does not explain.")
    print(f"  {'eval':>6}{'clock':>8}{'n':>7}{'score':>8}{'95% CI':>16}")
    for eb in (band, band // 2, band // 4, max(1, band // 10)):
        for cbx in (cb, cb / 2, cb / 10):
            v = []
            for g in games:
                for M in range(hi_M, lo_M - 1, -1):
                    if M in g["reached"]:
                        cp, mine, opp = g["reached"][M]
                        if (abs(cp) <= eb and abs(math.log(max(mine, .1) / max(opp, .1)))
                                <= math.log(1 + cbx)):
                            v.append(g["score"])
                        break
            if len(v) < 30:
                continue
            m, l2, h2 = boot(v)
            print(f"  {eb:6}{cbx:8.1%}{len(v):7}{100 * m:7.1f}%   "
                  f"[{100 * l2:5.1f},{100 * h2:5.1f}]")

    p = os.path.join(outdir, "material.csv")
    with open(p, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader(); wr.writerows(rows)
    print(f"\n-> {p}")


if __name__ == "__main__":
    main(sys.argv[1:])
