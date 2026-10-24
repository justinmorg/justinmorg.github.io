#!/usr/bin/env python3
"""payoff_stakes.py — per position bucket: own moves/game, P1 errors/game, and
two realized costs per P1 error. Input to payoff_model.py. Exploratory.

    python3 payoff_stakes.py FEATURES_DIR OUT_DIR [MATEDANGER.csv]

FEATURES_DIR: features.py on the six Lichess plateau blocks, --tc 180+2,300+0
(gate 4,691 games / 155,192 rows). Without MATEDANGER.csv, M2 is folded into
the other buckets and a provisional M2 row is added (share 5% of moves, P1
11.67% from vsopp, cost = MG level's) — that is how the 2026-10-24 run was
made (the full mate scan is ~3.7 h on 2 cores here).

Costs, game points per P1 error (P1 = wp_error >= 0.15):
  curve    f_phase(wp_before) - f_phase(wp_after), f = his own empirical
           final score by engine win-prob, 20 bins, phase op/mg/eg
  matched  games entering the bucket, quintiles of wp at entry; within
           quintile, slope of game score on # P1 errors in the bucket;
           n-weighted average. Smaller than curve (recovery inside the game
           is netted out; longer stays carry more errors).
Writes OUT_DIR/stakes_curve.csv and OUT_DIR/stakes_matched.csv.
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from buckets import assign, MATE_CP  # noqa: E402

AREAS = ["Opening", "MG level", "MG winning", "EG ahead", "EG level"]


def main():
    F, OUT = sys.argv[1], sys.argv[2]
    mdp = sys.argv[3] if len(sys.argv) > 3 else None
    m = pd.read_csv(f"{F}/moves.csv.gz", dtype={"block": str, "gid": str})
    g = pd.read_csv(f"{F}/games.csv", dtype={"block": str, "gid": str})
    if (len(g), len(m)) != (4691, 155192):
        sys.exit(f"GATE: {len(g)} / {len(m)}, expected 4,691 / 155,192")
    if mdp:
        m = m.merge(pd.read_csv(mdp, dtype={"gid": str}), on=["gid", "ply"], how="left")
        if m.loc[m.cp_before.abs() < MATE_CP, "a_null"].isna().any():
            sys.exit("GATE: mate scan incomplete")
    else:
        m["a_null"] = m["b_m1"] = m["c_check"] = 0
    m["bucket"] = assign(m)
    m = m.merge(g[["gid", "block", "score"]], on=["gid", "block"])
    m["e15"] = m.wp_error >= 0.15
    NG = len(g)

    # conversion curve
    m["phase"] = np.select([m.fullmove <= 12, m.npm_light <= 14], ["op", "eg"], "mg")
    bins = np.linspace(0, 1, 21); mids = (bins[:-1] + bins[1:]) / 2
    m["cost_curve"] = 0.0
    for ph, d in m.groupby("phase"):
        idx = np.clip(np.digitize(d.wp_before, bins) - 1, 0, 19)
        s = d.groupby(idx).score.mean().reindex(range(20)).interpolate().bfill().ffill()
        x, y = np.r_[0, mids, 1], np.r_[s.iloc[0], s.values, s.iloc[-1]]
        print(ph, "wp -> score:", " ".join(f"{a:.2f}:{b:.2f}" for a, b in
                                           zip(mids[::4], s.values[::4])))
        sel = m.phase == ph
        m.loc[sel, "cost_curve"] = (np.interp(m.loc[sel, "wp_before"], x, y)
                                    - np.interp(m.loc[sel, "wp_after"], x, y))

    rows = []
    for b, d in m.groupby("bucket"):
        e = d[d.e15]
        if not len(e): continue
        rows.append(dict(bucket=b, moves_pg=len(d) / NG, P1=100 * d.e15.mean(),
                         err_pg=len(e) / NG, wp_cost=e.wp_error.mean(),
                         real_cost=e.cost_curve.mean()))
    t = pd.DataFrame(rows).set_index("bucket")
    if not mdp:
        mpg = 0.05 * len(m) / NG
        t.loc["M2 mate danger"] = dict(moves_pg=mpg, P1=11.67, err_pg=mpg * .1167,
                                       wp_cost=np.nan, real_cost=t.loc["MG level", "real_cost"])

    # entry-matched cost
    matched = {}
    for a in AREAS:
        d = m[m.bucket == a].sort_values(["gid", "ply"])
        first = d.groupby("gid").first()
        first["nerr"] = d.groupby("gid").e15.sum()
        first["band"] = pd.qcut(first.wp_before, 5, duplicates="drop")
        sl = [(np.polyfit(x.nerr, x.score, 1)[0], len(x))
              for _, x in first.groupby("band", observed=True) if x.nerr.std() > 0]
        matched[a] = -np.average([s for s, _ in sl], weights=[n for _, n in sl])
    matched["M2 mate danger"] = matched["MG level"]

    tm = t.copy()
    for a, v in matched.items():
        tm.loc[a, "real_cost"] = v
    for tt, name in ((t, "curve"), (tm, "matched")):
        tt["pts_per100_real"] = 100 * tt.err_pg * tt.real_cost
        tt.sort_values("pts_per100_real", ascending=False).to_csv(f"{OUT}/stakes_{name}.csv")
        print(f"\n== cost: {name}")
        print(tt.sort_values("pts_per100_real", ascending=False).round(3).to_string())


if __name__ == "__main__":
    main()
