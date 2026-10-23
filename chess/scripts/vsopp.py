import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/claude/justinmorg.github.io/chess/scripts")
from buckets import assign, BLOCKS  # noqa: E402

S = sys.argv[1]
def load(fd, md):
    m = pd.read_csv(f"{S}/{fd}/moves.csv.gz", dtype={"block": str, "gid": str})
    m = m.merge(pd.read_csv(f"{S}/{md}", dtype={"gid": str}), on=["gid", "ply"], how="left")
    assert not m.loc[m.cp_before.abs() < 10000, "a_null"].isna().any()
    m["bucket"] = assign(m)
    m["e15"] = (m.wp_error >= 0.15).astype(float)
    m["wpl"] = m.wp_error.clip(lower=0)
    return m
me = load("featlic", "matedanger.csv"); op = load("featopp", "md_opp.csv")
assert set(me.gid) == set(op.gid)
g = pd.read_csv(f"{S}/featlic/games.csv", dtype={"block": str, "gid": str})
print("mean Elo me / opp:", round(g.my_elo.mean()), round(g.opp_elo.mean()))
print(g.groupby("block")[["my_elo", "opp_elo"]].mean().loc[BLOCKS].round(0).to_string())

BK = ["Opening", "MG winning", "MG level", "MG losing", "EG ahead", "EG level",
      "EG behind", "M1 mate for me", "M2 mate danger"]
games = np.array(sorted(set(me.gid))); gi = {k: i for i, k in enumerate(games)}
rng = np.random.default_rng(23); R = rng.integers(0, len(games), (2000, len(games)))
def per_game(d, b, col):
    s = d[d.bucket == b]; idx = s.gid.map(gi).to_numpy()
    return (np.bincount(idx, weights=s[col].to_numpy(), minlength=len(games)),
            np.bincount(idx, minlength=len(games)).astype(float))
rows = []
for b in BK:
    for col in ["e15", "wpl"]:
        sm, nm = per_game(me, b, col); so, no = per_game(op, b, col)
        vm, vo = sm.sum() / nm.sum(), so.sum() / no.sum()
        dm = sm[R].sum(1) / nm[R].sum(1) - so[R].sum(1) / no[R].sum(1)
        lo, hi = np.percentile(dm, [2.5, 97.5])
        rows.append(dict(bucket=b, metric=col, me=vm * 100, opp=vo * 100, diff=(vm - vo) * 100,
                         lo=lo * 100, hi=hi * 100, n_me=int(nm.sum()), n_opp=int(no.sum())))
r = pd.DataFrame(rows)
print("\npooled plateau, me vs opponents (points; diff = me - opp, 95% game bootstrap)")
print(r.round(2).to_string(index=False))

print("\nshare of moves by bucket (%)  me / opp")
print(pd.DataFrame({"me": me.bucket.value_counts(normalize=True) * 100,
                    "opp": op.bucket.value_counts(normalize=True) * 100}).round(1).to_string())
print("\ntotal win chance lost per game, me / opp:",
      round(me.wpl.sum() / len(games), 3), round(op.wpl.sum() / len(games), 3))
for nm_, d in [("me", me), ("opp", op)]:
    print(f"\n{nm_} P1 per block (%)")
    print((d.pivot_table(index="bucket", columns="block", values="e15", aggfunc="mean")[BLOCKS] * 100)
          .reindex(BK).round(2).to_string())

# ---- split by rating gap at the median, so halves are equal in games
gap = g.set_index("gid").opp_elo - g.set_index("gid").my_elo
med = gap.median()
print(f"\nrating gap (opp - me): median {med:.0f}, quartiles {gap.quantile(.25):.0f} / {gap.quantile(.75):.0f}")
hi_g = set(gap[gap > med].index); lo_g = set(gap[gap <= med].index)
print("games stronger half / weaker half:", len(hi_g), len(lo_g),
      " mean gap:", round(gap[list(hi_g)].mean()), round(gap[list(lo_g)].mean()))
sc = g.set_index("gid").score
print("my score vs stronger / weaker half:", round(sc[list(hi_g)].mean()*100, 1), round(sc[list(lo_g)].mean()*100, 1))
def rate_ci(d, gs, b, col):
    s = d[(d.bucket == b) & d.gid.isin(gs)]
    pg = s.groupby("gid")[col].agg(["sum", "count"])
    sv, nv = pg["sum"].to_numpy(), pg["count"].to_numpy()
    idx = rng.integers(0, len(sv), (1000, len(sv)))
    bs = sv[idx].sum(1) / nv[idx].sum(1)
    return sv.sum() / nv.sum() * 100, *(np.percentile(bs, [2.5, 97.5]) * 100), int(nv.sum())
rows = []
for b in BK:
    for who, d in [("opp", op), ("me", me)]:
        for half, gs in [("stronger", hi_g), ("weaker", lo_g)]:
            for col in ["e15", "wpl"]:
                v, l, h, n = rate_ci(d, gs, b, col)
                rows.append(dict(bucket=b, who=who, half=half, metric=col, v=v, lo=l, hi=h, n=n))
x = pd.DataFrame(rows)
x.to_csv(f"{S}/vsopp_split.csv", index=False)
for col in ["e15", "wpl"]:
    t = x[x.metric == col].pivot_table(index="bucket", columns=["who", "half"], values="v").reindex(BK)
    print(f"\n{col} by rating half"); print(t.round(2).to_string())
    t = x[x.metric == col].pivot_table(index="bucket", columns=["who", "half"], values="n").reindex(BK)
    if col == "e15": print("moves"); print(t.astype(int).to_string())
print("\n95% intervals, P1:")
print(x[x.metric == "e15"][["bucket", "who", "half", "v", "lo", "hi"]].round(2).to_string(index=False))

# ---- split by the opponent's own rating at its median (non-overlapping ranges)
oe = g.set_index("gid").opp_elo; me_e = g.set_index("gid").my_elo
omed = oe.median()
hiA = set(oe[oe > omed].index); loA = set(oe[oe <= omed].index)
print(f"\n==== ABSOLUTE split at opponent rating median {omed:.0f}")
print("  stronger-half opp rating range", int(oe[list(hiA)].min()), "-", int(oe[list(hiA)].max()),
      "mean", round(oe[list(hiA)].mean()), "| weaker-half", int(oe[list(loA)].min()), "-", int(oe[list(loA)].max()),
      "mean", round(oe[list(loA)].mean()))
print("  games", len(hiA), len(loA), "| my mean rating in those games", round(me_e[list(hiA)].mean()), round(me_e[list(loA)].mean()))
print("  my score", round(sc[list(hiA)].mean()*100, 1), round(sc[list(loA)].mean()*100, 1))
rows = []
for b in BK:
    for who, d in [("opp", op), ("me", me)]:
        for half, gs in [("stronger", hiA), ("weaker", loA)]:
            for col in ["e15", "wpl"]:
                v, l, h, n = rate_ci(d, gs, b, col)
                rows.append(dict(bucket=b, who=who, half=half, metric=col, v=v, lo=l, hi=h, n=n))
y = pd.DataFrame(rows); y.to_csv(f"{S}/vsopp_abs.csv", index=False)
for col in ["e15", "wpl"]:
    print(f"\n{col} by absolute opponent-rating half")
    print(y[y.metric == col].pivot_table(index="bucket", columns=["who", "half"], values="v").reindex(BK).round(2).to_string())
print("\n95% intervals, P1 (absolute split):")
print(y[y.metric == "e15"][["bucket", "who", "half", "v", "lo", "hi", "n"]].round(2).to_string(index=False))
