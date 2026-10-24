import numpy as np, pandas as pd
MATE = 10000
d = "/home/claude/panel"
ranks = pd.read_csv(f"{d}/panel_ranks_private.csv")
use = [p for p in range(1, 45) if p not in (7, 15, 35, 40)]
pl = ranks[ranks.pair.isin(use)]; grp = dict(zip(pl.id, pl.group))
m = pd.read_csv(f"{d}/feat/moves.csv.gz", dtype={"block": str, "gid": str},
                usecols=["block", "gid", "ply", "cp_before", "cp_after", "wp_error"])
md = pd.read_csv(f"{d}/feat/matedanger.csv", dtype={"gid": str}).drop_duplicates(["gid", "ply"])
m = m.merge(md, on=["gid", "ply"], how="left")
m["pid"] = m.block.str.split("_").str[0]; m["mon"] = m.block.str.split("_").str[1]
m = m[m.pid.isin(grp)]
nonmate = m.cp_before.abs() < MATE
m = m.assign(
    M1=(m.cp_before >= MATE).astype(int),
    M2=(nonmate & ((m.a_null == 1) | (m.b_m1 == 1) | (m.c_check == 1))).astype(int),
    NM=nonmate.astype(int))
m = m.assign(kept=(m.M1 == 1) & (m.cp_after >= MATE),
             walked2=(m.M2 == 1) & (m.cp_after <= -MATE),
             walked=(m.NM == 1) & (m.cp_after <= -MATE))
S = m.groupby(["pid", "mon"])[["M1", "kept", "M2", "walked2", "NM", "walked"]].sum()
pairs = pl.pivot(index="pair", columns="group", values="id")
def arr(g, mo): return S.reindex([(p, mo) for p in pairs[g]]).fillna(0).to_numpy()
A = {(g, mo): arr(g, mo) for g in ("improver", "control") for mo in ("2509", "2609")}
K = {"kept": (1, 0), "walked2": (3, 2), "walked": (5, 4)}
def rate(x, key): num, den = K[key]; return x[:, num].sum() / x[:, den].sum()
print("=== Panel rates (pooled)")
for key, lab, sc in (("kept", "kept a forced mate when they had one, %", 100),
                     ("walked2", "walked into forced mate in mate-danger positions, %", 100),
                     ("walked", "walked into forced mate, per 1000 non-mate moves", 1000)):
    print(f"  {lab}")
    for g in ("improver", "control"):
        print(f"    {g:8s} {sc*rate(A[(g,'2509')], key):6.2f} -> {sc*rate(A[(g,'2609')], key):6.2f}")
    rng = np.random.default_rng(23); n = len(pairs)
    def st(ix):
        return ((rate(A[("improver","2609")][ix], key) - rate(A[("improver","2509")][ix], key))
                - (rate(A[("control","2609")][ix], key) - rate(A[("control","2509")][ix], key)))
    o = st(np.arange(n)); b = [st(rng.integers(0, n, n)) for _ in range(2000)]
    lo, hi = np.percentile(b, [2.5, 97.5])
    print(f"    improver change minus control change {sc*o:+.2f} [{sc*lo:+.2f}, {sc*hi:+.2f}]")
print("  counts per group-month: forced-mate positions ~", int(A[("improver","2509")][:,0].sum()),
      "; mate-danger positions ~", int(A[("improver","2509")][:,2].sum()))
j = pd.read_csv("/home/claude/featme/moves.csv.gz", dtype={"gid": str}, usecols=["gid", "cp_before", "cp_after"])
j = j.assign(M1=(j.cp_before >= MATE).astype(int), NM=(j.cp_before.abs() < MATE).astype(int))
j = j.assign(kept=((j.M1 == 1) & (j.cp_after >= MATE)).astype(int), walked=((j.NM == 1) & (j.cp_after <= -MATE)).astype(int))
G = j.groupby("gid")[["M1", "kept", "NM", "walked"]].sum().to_numpy()
br = np.random.default_rng(23); B = []
for _ in range(2000):
    s = G[br.integers(0, len(G), len(G))].sum(0); B.append((100 * s[1] / s[0], 1000 * s[3] / s[2]))
B = np.array(B); s = G.sum(0)
print("\n=== Justin, Q3 2025 + Q4 2025 + 2026 to Aug 19 (2,106 games)")
print(f"  kept a forced mate: {100*s[1]/s[0]:.1f}% of {s[0]} positions  95% {np.percentile(B[:,0],[2.5,97.5]).round(1)}")
print(f"  walked into forced mate: {1000*s[3]/s[2]:.2f} per 1000  95% {np.percentile(B[:,1],[2.5,97.5]).round(2)}")
# panel Sep 2025 with a pair-free player bootstrap for the comparison
for g in ("improver", "control"):
    x = A[(g, "2509")]; rng = np.random.default_rng(23)
    bb = [(100*rate(x[i], "kept"), 1000*rate(x[i], "walked")) for i in [rng.integers(0, len(x), len(x)) for _ in range(2000)]]
    bb = np.array(bb)
    print(f"  panel {g:8s} Sep 2025: kept {100*rate(x,'kept'):.1f}% {np.percentile(bb[:,0],[2.5,97.5]).round(1)}, "
          f"walked {1000*rate(x,'walked'):.2f}/1000 {np.percentile(bb[:,1],[2.5,97.5]).round(2)}")
