#!/usr/bin/env python3
"""Clock-deficit decomposition — separating a clock effect from a difficulty effect.

The README's standing caveat: clock state at any crossing is downstream of the
middlegame that produced it, so "short of time" and "had a hard game" cannot be
separated, and nothing licenses moving faster.

The way out is that a clock ADVANTAGE has two sources with different confounding:
  - I moved fast          -> heavily confounded with my position's difficulty
  - the opponent is slow  -> much less so; opponent pace is largely their trait

  C1  score by (my clock tercile x opponent clock tercile) at fullmove 25.
      Both axes, each holding the other fixed. Still contaminated: pressing an
      opponent makes them slow, so their move-25 clock is partly my doing.
  C2  the quasi-instrument. Opponent pace measured over moves 1-12 — BEFORE
      middlegame difficulty diverges — predicting my score, standardized over
      my own opening pace and opponent Elo quartile.
  C3  rules out the main alternative: that fast opponents are simply better
      prepared and get better positions. Tests eval at move 12 across opponent
      pace, then re-runs C2 with eval@12 in the stratum set.

C2 restricted to 3+2, where the increment makes clock accrual identical for both
players at the same move number. 5+0 n is too small for the 3x3x4 strata.

Usage:
    python3 chess/scripts/clockdecomp.py /home/claude/features
"""
import os
import sys

import numpy as np
import pandas as pd

RNG = np.random.default_rng(23)


def load(d):
    m = pd.read_csv(os.path.join(d, "moves.csv.gz"), dtype={"block": str, "gid": str})
    g = pd.read_csv(os.path.join(d, "games.csv"), dtype={"block": str, "gid": str})
    if len(m) != 178_684 or m.gid.nunique() != 5_404:
        sys.exit(f"FATAL: expected the 5,404/178,684 seven-block run, got "
                 f"{m.gid.nunique():,}/{len(m):,}")
    print(f"gate OK: {m.gid.nunique():,} games / {len(m):,} rows")
    return m, g


def snapshot(m, fm, lo):
    """one row per game: my clock and opponent's at my last own move <= fm"""
    s = m[(m.fullmove <= fm) & m.clk.notna() & m.opp_clk.notna()]
    s = s.sort_values("ply").drop_duplicates("gid", keep="last")
    return s[s.fullmove >= lo][["gid", "block", "tc", "fullmove", "clk", "opp_clk"]]


def std_mean(df, key, lvl, strata, w):
    s = df[df[key] == lvl]
    mu = s.groupby(strata, observed=True).score.mean()
    c = mu.index.intersection(w.index)
    return float((mu[c] * w[c]).sum() / w[c].sum())


def perm_contrast(df, key, strata, w, n=3000):
    obs = std_mean(df, key, "slow", strata, w) - std_mean(df, key, "fast", strata, w)
    d = np.empty(n)
    for i in range(n):
        t = df.copy()
        t[key] = RNG.permutation(t[key].values)
        d[i] = std_mean(t, key, "slow", strata, w) - std_mean(t, key, "fast", strata, w)
    return obs, (np.sum(np.abs(d) >= abs(obs)) + 1) / (n + 1)


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
    m, g = load(d)

    print("\n=== C1: score by own clock x opponent clock at fullmove 25 ===")
    s25 = snapshot(m, 25, 23).merge(g[["gid", "score", "opp_elo"]], on="gid")
    for tc in ["180+2", "300+0"]:
        t = s25[s25.tc == tc].copy()
        if len(t) < 200:
            continue
        t["mine"] = pd.qcut(t.clk, 3, labels=["low", "mid", "high"])
        t["theirs"] = pd.qcut(t.opp_clk, 3, labels=["low", "mid", "high"])
        piv = t.pivot_table(index="mine", columns="theirs", values="score",
                            aggfunc="mean", observed=True) * 100
        print(f"\n  {tc}  n={len(t):,}   score %, rows = MY clock, cols = THEIR clock")
        print(piv.round(1).to_string())
        own = np.mean([piv.loc["high", c] - piv.loc["low", c] for c in piv.columns])
        opp = np.mean([piv.loc[r, "low"] - piv.loc[r, "high"] for r in piv.index])
        print(f"  gradient from MY clock (high-low, theirs fixed)  : {own:+.1f} pp")
        print(f"  gradient from THEIR clock (low-high, mine fixed) : {opp:+.1f} pp")

    print("\n=== C2: opponent's OPENING pace as a quasi-instrument (3+2) ===")
    d2 = snapshot(m, 12, 11).merge(g[["gid", "score", "opp_elo"]], on="gid")
    d2 = d2[d2.tc == "180+2"].copy()
    d2["opp_pace"] = pd.qcut(d2.opp_clk, 3, labels=["slow", "mid", "fast"])
    d2["my_pace"] = pd.qcut(d2.clk, 3, labels=["slow", "mid", "fast"])
    d2["eloq"] = pd.qcut(d2.opp_elo, 4, labels=False, duplicates="drop")
    print(f"  n={len(d2):,} games reaching move 11-12")
    strata = ["my_pace", "eloq"]
    w = d2.groupby(strata, observed=True).size() / len(d2)
    for lvl in ["slow", "mid", "fast"]:
        s = d2[d2.opp_pace == lvl]
        print(f"    opponent {lvl:5s}: raw {100*s.score.mean():.1f}%   "
              f"standardized {100*std_mean(d2,'opp_pace',lvl,strata,w):.1f}%   "
              f"n={len(s):,}  mean opp_elo {s.opp_elo.mean():.0f}")
    o, p = perm_contrast(d2, "opp_pace", strata, w)
    print(f"  opponent slow - fast, standardized: {100*o:+.1f} pp, two-sided p = {p:.4f}")

    print("\n  mirror (the CONFOUNDED arm): my own opening pace")
    w2 = d2.groupby(["opp_pace", "eloq"], observed=True).size() / len(d2)
    for lvl in ["slow", "mid", "fast"]:
        print(f"    me {lvl:5s}: standardized "
              f"{100*std_mean(d2,'my_pace',lvl,['opp_pace','eloq'],w2):.1f}%")
    print("  non-monotone -> still licenses nothing about your own speed.")

    print("\n=== C3: clock effect, or preparation effect? ===")
    e12 = (m[m.fullmove.between(11, 12) & (m.mate_flag == 0)]
           .sort_values("ply").drop_duplicates("gid", keep="last")[["gid", "cp_after"]])
    d3 = d2.merge(e12, on="gid")
    print("  my eval at move 12 by opponent's opening pace:")
    print(d3.groupby("opp_pace", observed=True)
          .agg(n=("cp_after", "size"), mean_cp=("cp_after", "mean"),
               median_cp=("cp_after", "median"),
               pct_worse=("cp_after", lambda x: 100 * (x < -100).mean()))
          .round(1).to_string())
    print("  -> flat. Fast opponents are NOT getting better positions.")
    d3["evb"] = pd.cut(d3.cp_after, [-1e9, -100, 100, 1e9],
                       labels=["I am worse", "level", "I am better"])
    piv = d3.pivot_table(index="evb", columns="opp_pace", values="score",
                         aggfunc="mean", observed=True) * 100
    print("\n  score by opponent pace WITHIN eval-at-12 bucket:")
    print(piv.round(1).to_string())
    strata3 = ["evb", "my_pace", "eloq"]
    w3 = d3.groupby(strata3, observed=True).size() / len(d3)
    o, p = perm_contrast(d3, "opp_pace", strata3, w3)
    print(f"\n  standardized over (eval@12 x my pace x opp Elo): "
          f"slow-fast {100*o:+.1f} pp, two-sided p = {p:.4f}")


if __name__ == "__main__":
    main()
