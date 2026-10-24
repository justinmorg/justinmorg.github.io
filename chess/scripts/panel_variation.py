import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/justinmorg.github.io/chess/scripts")
from panel_analyze import player_tables, AREAS, logit, MIN_MOVES
d = "/home/claude/panel"
ranks = pd.read_csv(f"{d}/panel_ranks_private.csv")
use_pairs = [p for p in range(1, 45) if p not in (7, 15, 35, 40)]
pl = ranks[ranks.pair.isin(use_pairs)]
rating = dict(zip(pl.id, pl.mean_2509)); grp = dict(zip(pl.id, pl.group))
t, m = player_tables(d, 1, 44)
t = t[t.pid.isin(rating)]
# Sep 2025 full month and halves
t25 = t[t.half.isin(["A", "B"])].copy()
full = t25.groupby(["pid", "bucket"])[["sum", "count"]].sum().reset_index(); full["half"] = "F"
T = pd.concat([t25, full])
rows = []
for h in ["A", "B", "F"]:
    sub = T[T.half == h].copy()
    sub["L"] = logit(sub["sum"], sub["count"]); sub["rating"] = sub.pid.map(rating)
    for a in AREAS:
        s = sub[(sub.bucket == a) & (sub["count"] >= (MIN_MOVES if h != "F" else 2 * MIN_MOVES))]
        X = np.c_[np.ones(len(s)), s.rating]; w = s["count"].to_numpy()
        b = np.linalg.lstsq(X * np.sqrt(w)[:, None], s.L * np.sqrt(w), rcond=None)[0]
        p = (s["sum"] + .5) / (s["count"] + 1)
        for (pid, L, r, n, pp) in zip(s.pid, s.L, s.rating, s["count"], p):
            rows.append(dict(half=h, pid=pid, area=a, R=L - b[0] - b[1] * r,
                             noise_var=1 / (n * pp * (1 - pp)), n=n, rate=pp))
R = pd.DataFrame(rows)
F = R[R.half == "F"]
print("=== Spread of relative strength across players (Sep 2025, full month)")
print(f"{'area':15s} {'players':>7s} {'base%':>6s} {'obs SD':>7s} {'noise SD':>8s} {'true SD':>7s} {'split-half r':>12s}")
W = R[R.half.isin(["A", "B"])].pivot_table(index=["pid", "area"], columns="half", values="R").dropna()
for a in AREAS:
    f = F[F.area == a]
    obs = f.R.var(ddof=1); noise = f.noise_var.mean(); true = max(obs - noise, 0)
    w = W.xs(a, level="area")
    r = np.corrcoef(w.A, w.B)[0, 1]
    print(f"{a:15s} {len(f):7d} {100*f.rate.mean():6.1f} {np.sqrt(obs):7.2f} {np.sqrt(noise):8.2f} {np.sqrt(true):7.2f} {r:12.2f}")
# translate a true SD into error rates at the base rate
print("\n=== What 1 true SD means at the base rate (better / worse than a peer at the same rating)")
for a in AREAS:
    f = F[F.area == a]; obs = f.R.var(ddof=1); true = np.sqrt(max(obs - f.noise_var.mean(), 0))
    base = f.rate.mean(); lb = np.log(base / (1 - base))
    lo, hi = [1 / (1 + np.exp(-(lb + k))) for k in (-true, true)]
    print(f"{a:15s} {100*lo:5.1f}% .. {100*base:5.1f}% .. {100*hi:5.1f}%")
# correlation between areas: general factor?
P = F.pivot(index="pid", columns="area", values="R")[AREAS]
print("\n=== Correlation between areas (relative strength, Sep 2025)")
print(P.corr().round(2).to_string())
print("mean off-diagonal r:", round(P.corr().values[np.triu_indices(6, 1)].mean(), 2))
# best/worst consistency between halves
print("\n=== Is a player's best / worst area stable between the two halves of the month?")
agree_b = agree_w = n = 0; chance = 0
for pid, g in W.groupby(level="pid"):
    g = g.droplevel("pid")
    if len(g) < 5: continue
    n += 1; chance += 1 / len(g)
    agree_b += g.A.idxmin() == g.B.idxmin(); agree_w += g.A.idxmax() == g.B.idxmax()
print(f"players {n}: best area agrees {agree_b} ({100*agree_b/n:.0f}%), worst agrees {agree_w} ({100*agree_w/n:.0f}%), chance ~{100*chance/n:.0f}%")
print("\n=== Which area is each player's best / worst (full Sep 2025)")
bw = pd.DataFrame({"best": P.idxmin(axis=1), "worst": P.idxmax(axis=1)})
print(pd.concat([bw.best.value_counts(), bw.worst.value_counts()], axis=1).reindex(AREAS).fillna(0).astype(int).to_string())
print("\n=== Within-player spread: best minus worst area, log-odds (full month)")
spread = P.max(axis=1) - P.min(axis=1)
print(spread.describe().round(2).to_string())
print("\n=== Improvers vs controls: spread of profile")
for gname in ("improver", "control"):
    ids = [p for p in P.index if grp[p] == gname]
    print(gname, "mean within-player spread", round(spread[ids].mean(), 2),
          "| mean R by area:", " ".join(f"{a.split()[0][:4]}{P.loc[ids, a].mean():+.2f}" for a in AREAS))
