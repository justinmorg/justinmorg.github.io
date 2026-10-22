#!/usr/bin/env python3
"""
buckets.py — error rate by position bucket over time. Implements
buckets_prespec.md exactly; change that file first if anything here changes.

Usage:
    python3 buckets.py FEATURES_DIR MATEDANGER.csv [--draws 20000]

FEATURES_DIR: features.py on the six Lichess blocks (2024H2, Q1-2025 ..
Q4-2025, 2026), --tc 180+2,300+0. MATEDANGER.csv: matedanger.py output.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

BLOCKS = ["2024H2", "Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025", "2026"]
MATE_CP = 10000
TESTED = ["M1 mate for me", "M2 mate danger", "Opening", "MG winning", "MG level",
          "MG losing", "EG ahead", "EG level", "EG behind"]
ORDER = TESTED[:2] + ["M3 mate against me"] + TESTED[2:]


def assign(m):
    cp, fm, npm = m.cp_before, m.fullmove, m.npm_light
    danger = (m.a_null == 1) | (m.b_m1 == 1) | (m.c_check == 1)
    conds = [cp >= MATE_CP, cp <= -MATE_CP, danger, fm <= 12,
             (npm <= 14) & (cp > 100), (npm <= 14) & (cp > -100), npm <= 14,
             cp >= 150, cp > -150]
    labels = ["M1 mate for me", "M3 mate against me", "M2 mate danger", "Opening",
              "EG ahead", "EG level", "EG behind", "MG winning", "MG level"]
    return np.select(conds, labels, "MG losing")


def wls_slope(x, y, w):
    w = np.where(np.isfinite(y), w, 0.0)
    y = np.nan_to_num(y)
    sw = w.sum(-1, keepdims=True)
    xm = (w * x).sum(-1, keepdims=True) / sw
    ym = (w * y).sum(-1, keepdims=True) / sw
    return ((w * (x - xm) * (y - ym)).sum(-1) / (w * (x - xm) ** 2).sum(-1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("matedanger")
    ap.add_argument("--draws", type=int, default=20000)
    a = ap.parse_args()

    m = pd.read_csv(os.path.join(a.features, "moves.csv.gz"),
                    dtype={"block": str, "gid": str})
    g = pd.read_csv(os.path.join(a.features, "games.csv"), dtype={"block": str, "gid": str})
    md = pd.read_csv(a.matedanger, dtype={"gid": str})

    # ---- gates
    if set(m.block) != set(BLOCKS) or (m.site != "lichess").any():
        sys.exit(f"GATE: blocks {sorted(set(m.block))}")
    if (len(g), len(m)) != (4691, 155192):
        sys.exit(f"GATE: {len(g)} games / {len(m)} rows, expected 4,691 / 155,192")
    if pd.to_datetime(g.date, format="%Y-%m-%d").max() >= pd.Timestamp("2026-09-03"):
        sys.exit("GATE: a game on/after 2026-09-03 (group F treatment block)")
    m = m.merge(md, on=["gid", "ply"], how="left")
    need = m.cp_before.abs() < MATE_CP
    if m.loc[need, "a_null"].isna().any():
        sys.exit(f"GATE: {m.loc[need, 'a_null'].isna().sum()} positions missing from scan")
    known = need & (m.fullmove > 12) & (m.cp_after <= -MATE_CP)
    flagged = ((m.a_null == 1) | (m.b_m1 == 1) | (m.c_check == 1))[known].sum()
    print(f"M2 gate: {flagged} of {known.sum()} known walked-into-mate positions flagged "
          f"(coverage test floor 1,055)")
    if flagged < 1055:
        sys.exit("GATE: M2 coverage below the coverage-test floor")

    m["bucket"] = assign(m)
    assert m.bucket.notna().all() and len(m) == 155192
    m["e15"] = (m.wp_error >= 0.15).astype(float)
    m["wpl"] = m.wp_error.clip(lower=0)
    m["cp200"] = (m.drop_cp >= 200).astype(float)

    dates = pd.to_datetime(g.date, format="%Y-%m-%d")
    g["d"] = dates
    rng_ = g.groupby("block").d.agg(["min", "max"])
    mid = (rng_["min"] + (rng_["max"] - rng_["min"]) / 2).loc[BLOCKS]
    x = ((mid - mid.iloc[0]).dt.days / 365.25).to_numpy()

    def report(d, scope, test):
        print(f"\n==================== {scope}")
        games = d.gid.unique()
        gi = {k: i for i, k in enumerate(games)}
        gblock = d.drop_duplicates("gid").set_index("gid").block.map(
            {b: i for i, b in enumerate(BLOCKS)}).loc[games].to_numpy()
        print("\nshare of moves per block (%):")
        sh = pd.crosstab(d.bucket, d.block, normalize="columns")[BLOCKS] * 100
        print(sh.reindex(ORDER).round(1).to_string())
        print("\nmoves per block:")
        print(pd.crosstab(d.bucket, d.block)[BLOCKS].reindex(ORDER).to_string())
        print("\nmean cp_before per block (composition):")
        print(d[d.cp_before.abs() < MATE_CP].pivot_table(
            index="bucket", columns="block", values="cp_before", aggfunc="mean")[BLOCKS]
              .reindex(ORDER).round(0).to_string())
        for col, lab in [("e15", "P1 error rate, wp drop >= 15 pts (%)"),
                         ("wpl", "P2 win chance lost per move (pts)"),
                         ("cp200", "secondary: drop >= 200cp (%)")]:
            print(f"\n{lab}:")
            print((d.pivot_table(index="bucket", columns="block", values=col,
                                 aggfunc="mean")[BLOCKS] * 100).reindex(ORDER)
                  .round(2).to_string())
        # per-game sums for every (bucket, metric), then shuffle block labels
        cols, N_g, S_g = [], [], []
        for b in TESTED:
            sub = d[d.bucket == b]
            idx = sub.gid.map(gi).to_numpy()
            n_g = np.bincount(idx, minlength=len(games)).astype(float)
            for col in ["e15", "wpl"]:
                cols.append((b, col)); N_g.append(n_g)
                S_g.append(np.bincount(idx, weights=sub[col].to_numpy(), minlength=len(games)))
        N_g, S_g = np.array(N_g).T, np.array(S_g).T          # games x 18
        onehot = np.eye(6)[gblock]                              # games x 6
        N_b, S_b = onehot.T @ N_g, onehot.T @ S_g               # 6 x 18
        with np.errstate(invalid="ignore", divide="ignore"):
            obs = wls_slope(x, (S_b / N_b).T, N_b.T)            # 18
        res = [dict(bucket=b, metric=c, slope=obs[i]) for i, (b, c) in enumerate(cols)]
        if test:
            rs = np.random.default_rng(23)
            exceed = np.zeros(len(cols))
            for start in range(0, a.draws, 500):
                k = min(500, a.draws - start)
                perms = np.stack([rs.permutation(gblock) for _ in range(k)])   # k x games
                Nn = np.stack([(perms == j).astype(float) @ N_g for j in range(6)], 1)  # k x 6 x 18
                Ss = np.stack([(perms == j).astype(float) @ S_g for j in range(6)], 1)
                with np.errstate(invalid="ignore", divide="ignore"):
                    null = wls_slope(x[None, None, :], np.moveaxis(Ss / Nn, 1, 2),
                                     np.moveaxis(Nn, 1, 2))    # k x 18
                exceed += (np.abs(null) >= np.abs(obs)[None, :]).sum(0)
            br = np.random.default_rng(23)
            e0, e5 = np.where(gblock == 0)[0], np.where(gblock == 5)[0]
            r0 = br.integers(0, len(e0), (2000, len(e0))); r5 = br.integers(0, len(e5), (2000, len(e5)))
            for i, r in enumerate(res):
                r["p"] = (1 + exceed[i]) / (1 + a.draws)
                r["end_diff"] = S_b[5, i] / N_b[5, i] - S_b[0, i] / N_b[0, i]
                d5 = S_g[e5, i][r5].sum(1) / N_g[e5, i][r5].sum(1)
                d0 = S_g[e0, i][r0].sum(1) / N_g[e0, i][r0].sum(1)
                r["lo"], r["hi"] = np.nanpercentile(d5 - d0, [2.5, 97.5])
        return pd.DataFrame(res)

    prim = report(m, "PRIMARY: 3+2 and 5+0", True)
    rob = report(m[m.tc == "180+2"], "ROBUSTNESS: 3+2 only", False)

    # Holm across the 18 primary tests
    prim = prim.sort_values("p").reset_index(drop=True)
    k = len(prim)
    holm = np.maximum.accumulate((k - np.arange(k)) * prim.p.to_numpy())
    prim["p_holm"] = np.minimum(holm, 1.0)
    prim = prim.merge(rob[["bucket", "metric", "slope"]].rename(columns={"slope": "slope_32"}),
                      on=["bucket", "metric"])
    prim["moved"] = (prim.p_holm < 0.05) & (np.sign(prim.slope) == np.sign(prim.slope_32))
    for c in ["slope", "slope_32", "end_diff", "lo", "hi"]:
        prim[c] = prim[c] * 100
    print("\n==================== TEST (slopes in points per year; endpoint = 2026 minus 2024 H2, "
          "points, with 95% bootstrap interval)")
    print(prim.sort_values(["metric", "bucket"]).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
