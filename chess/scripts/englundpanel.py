#!/usr/bin/env python3
"""
englundpanel.py — does the Englund's edge fade with the 1.d4 player's rating?
Exploratory, not pre-specified (2026-10-24). No evals; ratings and results only.

Usage:
    python3 englundpanel.py RAW_DIR

RAW_DIR: raw_2509.tar.gz + raw_2609.tar.gz from chess/data/panel, extracted.
Every rated 3+2/5+0 game opening 1.d4 in the panel files, deduped by GameId
(either side may be the panel player). Outcome: Black's score minus Elo
expectation ("over"). The Englund edge is Englund over minus the over of every
other reply to 1.d4 at the same White rating, which cancels White's general
first-move edge. Trend: OLS over ~ E + x + E:x with x = (WhiteElo - 1450)/200,
intervals by bootstrap over panel players (2,000 draws, seed 23) — Englund
games cluster on the panel players who play it.
"quick" = Black win in <= 25 moves, a crude no-engine proxy for a trap landing.
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

HDR = re.compile(r'^\[(\w+) "(.*)"\]$')


def games(path):
    with open(path) as f:
        h = {}
        for line in f:
            line = line.rstrip("\n")
            m = HDR.match(line)
            if m:
                h[m.group(1)] = m.group(2)
            elif line.startswith("1."):
                yield h, line
                h = {}


def load(raw):
    rows, seen = [], set()
    for p in sorted(glob.glob(os.path.join(raw, "*.pgn"))):
        for h, mv in games(p):
            gid = h.get("GameId")
            if gid in seen or h.get("TimeControl") not in ("180+2", "300+0"):
                continue
            seen.add(gid)
            t = [x for x in re.sub(r"\{[^}]*\}", "", mv).split() if not re.match(r"^\d+\.+$", x)]
            if len(t) < 2 or t[0] != "d4":
                continue
            res = {"1-0": 0.0, "0-1": 1.0, "1/2-1/2": 0.5}.get(h.get("Result"))
            try:
                we, be = int(h["WhiteElo"]), int(h["BlackElo"])
            except (KeyError, ValueError):
                continue
            if res is None:
                continue
            pid = h["White"] if h["White"].startswith("P") else h["Black"]
            rows.append(dict(gid=gid, pid=pid, we=we, be=be, bscore=res, englund=t[1] == "e5",
                             third=t[2] if len(t) > 2 else "", n=len(t)))
    d = pd.DataFrame(rows)
    d["exp"] = 1 / (1 + 10 ** ((d.we - d.be) / 400))
    d["over"] = d.bscore - d.exp
    d["quick"] = (d.bscore == 1) & (d.n <= 50)
    return d


def fit(d):
    x = (d.we.to_numpy() - 1450) / 200
    e = d.englund.to_numpy(float)
    X = np.c_[np.ones(len(d)), e, x, e * x]
    b = np.linalg.lstsq(X, d.over.to_numpy(), rcond=None)[0]
    return np.array([b[1] - b[3], b[1], b[1] + b[3], b[3]])  # edge @1250, @1450, @1650, slope


def main():
    d = load(sys.argv[1])
    print(f"1.d4 games: {len(d)}  Englund: {int(d.englund.sum())}")
    d["band"] = pd.cut(d.we, [0, 1250, 1450, 1650, 9999],
                       labels=["<1250", "1250-1449", "1450-1649", "1650+"])
    for band, g in d.groupby("band", observed=True):
        e, o = g[g.englund], g[~g.englund]
        print(f"{band:10s} Englund n={len(e):4d} score={e.bscore.mean() * 100:5.1f} "
              f"exp={e.exp.mean() * 100:5.1f} | edge vs other replies "
              f"{(e.over.mean() - o.over.mean()) * 100:+5.1f} | quick win "
              f"{e.quick.mean() * 100:4.1f}% vs {o.quick.mean() * 100:4.1f}% | "
              f"2.dxe5 {(e.third == 'dxe5').mean() * 100:.0f}%")
    est = fit(d)
    idx = d.groupby("pid").indices
    keys = list(idx)
    rng = np.random.default_rng(23)
    bs = np.array([fit(d.iloc[np.concatenate([idx[k] for k in rng.choice(keys, len(keys))])])
                   for _ in range(2000)]) * 100
    for i, name in enumerate(["edge @1250", "edge @1450", "edge @1650", "slope per 200"]):
        lo, hi = np.percentile(bs[:, i], [2.5, 97.5])
        print(f"{name:14s} {est[i] * 100:+5.1f}  95% [{lo:+.1f}, {hi:+.1f}]")
    print(f"one-sided p(slope >= 0) = {(bs[:, 3] >= 0).mean():.3f}")


if __name__ == "__main__":
    main()
