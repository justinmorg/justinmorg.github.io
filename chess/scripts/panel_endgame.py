import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/justinmorg.github.io/chess/scripts")
from panel_analyze import player_tables, logit, MIN_MOVES
d = "/home/claude/panel"
ranks = pd.read_csv(f"{d}/panel_ranks_private.csv")
use = [p for p in range(1, 45) if p not in (7, 15, 35, 40)]
pl = ranks[ranks.pair.isin(use)]
grp = dict(zip(pl.id, pl.group)); pair = dict(zip(pl.id, pl.pair)); rating = dict(zip(pl.id, pl.mean_2509))
t, m = player_tables(d, 1, 44)
m = m[m.pid.isin(grp)].copy(); m["group"] = m.pid.map(grp)
m["mon"] = np.where(m.half == "S26", "2609", "2509")
EG = ["EG ahead", "EG level"]
rng = np.random.default_rng(23)
pairs = np.array(use)
def rates(sub):
    # per pair: improver and control rate change (pooled moves within player-month)
    out = {}
    g = sub.groupby(["pid", "mon"]).e15.agg(["sum", "count"])
    for p in pairs:
        ids = pl[pl.pair == p].set_index("group").id
        row = {}
        for gname in ("improver", "control"):
            for mon in ("2509", "2609"):
                k = (ids[gname], mon)
                row[(gname, mon)] = g.loc[k].values if k in g.index else np.array([0., 0.])
        out[p] = row
    return out
print("=== Raw endgame P1 error rates, pooled over players (Sep 2025 -> Sep 2026)")
for a in EG + ["Opening"]:
    sub = m[m.bucket == a]
    R = rates(sub)
    def pooled(sel, gname, mon):
        s = sum(R[p][(gname, mon)][0] for p in sel); n = sum(R[p][(gname, mon)][1] for p in sel)
        return s / n
    def stat(sel):
        ci = pooled(sel, "improver", "2609") - pooled(sel, "improver", "2509")
        cc = pooled(sel, "control", "2609") - pooled(sel, "control", "2509")
        return ci, cc, ci - cc
    obs = stat(pairs)
    boots = np.array([stat(rng.choice(pairs, len(pairs))) for _ in range(2000)])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    print(f"{a:9s} improvers {100*pooled(pairs,'improver','2509'):5.2f} -> {100*pooled(pairs,'improver','2609'):5.2f}%"
          f"   controls {100*pooled(pairs,'control','2509'):5.2f} -> {100*pooled(pairs,'control','2609'):5.2f}%"
          f"   difference in change {100*obs[2]:+.2f} pts [{100*lo[2]:+.2f}, {100*hi[2]:+.2f}]")
    print(f"{'':9s} moves per player-month, median: "
          f"{int(sub.groupby(['pid','mon']).size().median())}")
# composition: standardise EG ahead to pooled eval-band mix
print("\n=== EG ahead standardised to a common eval-band mix (post hoc)")
sub = m[(m.bucket == "EG ahead") & (m.cp_before.abs() < 10000)].copy()
sub["band"] = pd.cut(sub.cp_before, [100, 200, 300, 500, 800, 10000])
w = sub.band.value_counts(normalize=True)
for gname in ("improver", "control"):
    for mon in ("2509", "2609"):
        s = sub[(sub.group == gname) & (sub.mon == mon)]
        r = s.groupby("band", observed=False).e15.mean()
        print(f"  {gname:8s} {mon}: raw {100*s.e15.mean():5.2f}%  standardised {100*(r*w).sum():5.2f}%  mean eval {s.cp_before.mean():.0f}")
# did endgame-weak improvers improve more in endgames? profile on half A, change on half B
print("\n=== Endgame-weak vs endgame-strong in Sep 2025 (profile on half A, change on B)")
tt = t[t.pid.isin(grp)]
for a in EG:
    x = tt[tt.bucket == a].pivot_table(index="pid", columns="half", values=["sum", "count"]).fillna(0)
    ok = (x["count"][["A", "B", "S26"]] >= 60).all(axis=1)   # looser than the pre-spec's 100: exploratory
    x = x[ok]
    LA = logit(x["sum"]["A"], x["count"]["A"]); LB = logit(x["sum"]["B"], x["count"]["B"]); L26 = logit(x["sum"]["S26"], x["count"]["S26"])
    r = np.array([rating[p] for p in x.index])
    b = np.polyfit(r, LA, 1); RA = LA - np.polyval(b, r)
    I = LB - L26
    df = pd.DataFrame({"R": RA, "I": I, "g": [grp[p] for p in x.index]})
    for gname in ("improver", "control"):
        dg = df[df.g == gname]; med = df.R.median()
        weak, strong = dg[dg.R > med], dg[dg.R <= med]
        print(f"  {a:9s} {gname:8s} weak half improved {weak.I.mean():+.2f} (n={len(weak)}), "
              f"strong half {strong.I.mean():+.2f} (n={len(strong)})  [log-odds; + = fewer errors]")
