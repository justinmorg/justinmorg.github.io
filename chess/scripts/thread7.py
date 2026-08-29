#!/usr/bin/env python3
"""Thread 7 — does error SEVERITY skew fast inside the hot zone?

Frequency is settled: hot-zone errors are considered moves (median 8s, only 13%
at <=2s). The open claim, raised by several group R notes, is that the *worst*
ones are snap moves — that severity and frequency run opposite. If true it
identifies a subset worth pausing on, and partially rehabilitates a scan-style
drill format the think-time data otherwise undercuts.

PRE-SPECIFIED before any output was inspected:
  T1  mean wp_error by spend bin over the 633 permanent hot-zone drops
  T2  tail: share of the top wp_error decile played at <=2s, vs the 13% base
  T3  T1 holding position sharpness fixed (n_legal tercile x n_caps_avail
      x eval bucket), direct standardization
  DECISION RULE: T1 must decline roughly monotonically with spend AND T2 must
  clear the base rate. Otherwise the claim fails.

T4 and T5 were added AFTER seeing a directional lean in T1/T3 and are labelled
post-hoc wherever they appear. They do not rescue the pre-specified rule.

One first drop per game, so rows are already game-independent — no clustering.

Usage:
    python3 chess/scripts/firstdrop.py /home/claude/features   # prerequisite
    python3 chess/scripts/thread7.py   /home/claude/features
"""
import os
import sys

import numpy as np
import pandas as pd

RNG = np.random.default_rng(23)
BINS = [-0.01, 2, 4, 8, 16, 1e9]
LBL = ["<=2s", "2-4s", "4-8s", "8-16s", "16s+"]


def load(d):
    m = pd.read_csv(os.path.join(d, "moves.csv.gz"), dtype={"block": str, "gid": str})
    fd = pd.read_csv(os.path.join(d, "firstdrop", "firstdrop_200.csv"),
                     dtype={"block": str, "gid": str})
    lg = pd.read_csv(os.path.join(d, "firstdrop", "level_games.csv"),
                     dtype={"block": str, "gid": str})
    if len(m) != 178_684 or m.gid.nunique() != 5_404:
        sys.exit(f"FATAL: expected the 5,404/178,684 seven-block run, got "
                 f"{m.gid.nunique():,}/{len(m):,}")
    lev = lg[lg.entry_bucket == "level"]
    fdl = fd[fd.gid.isin(set(lev.gid))]
    hot = fdl[(~fdl.rec5) & fdl.fullmove.between(13, 25) & (fdl.npm_light >= 13)].copy()
    if len(hot) != 633 or hot.gid.nunique() != 633:
        sys.exit(f"FATAL: hot zone should be 633 games, got {len(hot)}")
    print(f"gate OK: hot zone n={len(hot)}, one drop per game; "
          f"median spend {hot.spend.median():.1f}s, "
          f"<=2s share {100*(hot.spend<=2).mean():.0f}%")
    return m, hot


def prep(m, hot):
    hot = hot.join(m.set_index(["gid", "ply"])[["n_legal", "n_caps_avail"]],
                   on=["gid", "ply"])
    hot = hot[hot.spend.between(0, 60)].copy()      # clock-sanity
    hot["sb"] = pd.cut(hot.spend, BINS, labels=LBL)
    hot["legq"] = pd.qcut(hot.n_legal, 3, labels=False, duplicates="drop")
    hot["capb"] = np.clip(hot.n_caps_avail, 0, 3)
    hot["evb"] = pd.cut(hot.cp_before, [-1e9, -50, 50, 1e9], labels=False)
    hot["stratum"] = (hot.legq.astype(str) + "|" + hot.capb.astype(str) + "|"
                      + hot.evb.astype(str))
    print(f"after clock-sanity filter (0<=spend<=60): n={len(hot)}")
    return hot


def boot_ci(x, n=4000):
    x = np.asarray(x)
    d = [np.mean(x[RNG.integers(0, len(x), len(x))]) for _ in range(n)]
    return np.percentile(d, [2.5, 97.5])


def standardized(hot, spend, w):
    """weighted mean wp_error for fast and slow arms over common strata"""
    out = []
    for msk in (spend <= 2, spend >= 8):
        s = hot[msk.values]
        mu = s.groupby("stratum").wp_error.mean()
        c = mu.index.intersection(w.index)
        out.append(float((mu[c] * w[c]).sum() / w[c].sum()))
    return out


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
    m, hot = load(d)
    hot = prep(m, hot)
    w = hot.groupby("stratum").size() / len(hot)

    print("\n--- T1 (pre-specified): severity by spend bin ---")
    print(f"{'bin':6s} {'n':>4s} {'mean wp_error':>14s} {'95% CI':>18s} {'median':>8s}")
    for b in LBL:
        s = hot[hot.sb == b].wp_error
        lo, hi = boot_ci(s)
        print(f"{b:6s} {len(s):4d} {s.mean():14.4f}  [{lo:.4f},{hi:.4f}] {s.median():8.4f}")
    print("  NOT monotone: 2-4s is the peak and 16s+ turns back up.")

    print("\n--- T2 (pre-specified): tail ---")
    base = (hot.spend <= 2).mean()
    for q, name in [(0.90, "top decile"), (0.75, "top quartile")]:
        thr = hot.wp_error.quantile(q)
        tail = hot[hot.wp_error >= thr]
        obs = (tail.spend <= 2).mean()
        perm = np.array([(hot.spend.values[RNG.permutation(len(hot))][
            hot.wp_error.values >= thr] <= 2).mean() for _ in range(5000)])
        print(f"  {name} (n={len(tail)}): {100*obs:.1f}% at <=2s vs base "
              f"{100*base:.1f}%  p={(np.sum(perm>=obs)+1)/5001:.3f}")
    print("  T2 is NULL. With T1 non-monotone, the DECISION RULE FAILS.")

    print("\n--- T3 (pre-specified): holding sharpness fixed ---")
    f, s = standardized(hot, hot.spend, w)
    print(f"  fast <=2s standardized {f:.4f} (n={int((hot.spend<=2).sum())})")
    print(f"  slow >=8s standardized {s:.4f} (n={int((hot.spend>=8).sum())})")
    print(f"  fast - slow = {f-s:+.4f}")

    print("\n--- T4 (POST-HOC, added after seeing the lean) ---")
    obs = f - s
    perm = np.array([np.subtract(*standardized(
        hot, pd.Series(RNG.permutation(hot.spend.values), index=hot.index), w))
        for _ in range(3000)])
    print(f"  standardized fast-slow {obs:+.4f}, permutation p = "
          f"{(np.sum(perm>=obs)+1)/3001:.3f}")
    thr = hot.wp_error.quantile(0.90)
    dm = hot[hot.wp_error >= thr].spend.median() - hot[hot.wp_error < thr].spend.median()
    pm = np.array([(lambda x: np.median(x[hot.wp_error.values >= thr])
                    - np.median(x[hot.wp_error.values < thr]))(
        RNG.permutation(hot.spend.values)) for _ in range(3000)])
    print(f"  median spend, top decile minus rest {dm:+.1f}s, p = "
          f"{(np.sum(pm<=dm)+1)/3001:.3f}")

    print("\n--- T5 (POST-HOC): does the T4 lean hold on independent splits? ---")
    h2 = hot.join(m.set_index(["gid", "ply"])[["site"]], on=["gid", "ply"])
    for name, sub in [("Lichess", h2[h2.site == "lichess"]),
                      ("chess.com", h2[h2.site != "lichess"]),
                      ("2024-25 blocks", h2[~h2.block.isin(["2026", "CC-2026"])]),
                      ("2026 blocks", h2[h2.block.isin(["2026", "CC-2026"])])]:
        ww = sub.groupby("stratum").size() / len(sub)
        a, b = standardized(sub, sub.spend, ww)
        print(f"  {name:16s} fast-slow {a-b:+.4f}   "
              f"n_fast={int((sub.spend<=2).sum()):3d} n_slow={int((sub.spend>=8).sum()):3d}")
    print("\nVERDICT: pre-specified claim fails. Residual lean is a flag, not a")
    print("finding — post-hoc, fast arm n=83, chess.com arm n=8.")


if __name__ == "__main__":
    main()
