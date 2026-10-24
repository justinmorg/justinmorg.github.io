import sys, io, re, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/justinmorg.github.io/chess/scripts")
from panel_analyze import player_tables, per_player, eco_overlap, AREAS, signflip
d = "/home/claude/panel"
ranks = pd.read_csv(f"{d}/panel_ranks_private.csv")
use = [p for p in range(1, 45) if p not in (7, 15, 35, 40)]
pl = ranks[ranks.pair.isin(use)]
grp = dict(zip(pl.id, pl.group)); rating = dict(zip(pl.id, pl.mean_2509))
t, m = player_tables(d, 1, 44)
st, _ = per_player(t, rating, list(pl.id))
st["nonopen"] = st[[f"I_{a}" for a in AREAS if a != "Opening"]].mean(axis=1)
MV = re.compile(r"^1\. (\S+)(?: \{[^}]*\})? 1\.\.\. (\S+)", re.S)
def own(pid, yymm):
    c = {"W": {}, "Be4": {}, "Bd4": {}}
    for g in open(f"{d}/pm/{pid}_{yymm}.pgn").read().split("[Event ")[1:]:
        w = g.split('[White "', 1)[1].split('"', 1)[0]
        body = g.split("\n\n", 1)[1] if "\n\n" in g else ""
        mm = MV.search(body.strip())
        if not mm: continue
        a, b = mm.groups()
        if w == pid: k, v = "W", a
        elif a in ("e4", "d4"): k, v = "B" + a, b
        else: continue
        c[k][v] = c[k].get(v, 0) + 1
    return c
def overlap(pid):
    A, B = own(pid, "2509"), own(pid, "2609"); acc = tot = 0
    for k in A:
        na, nb = sum(A[k].values()), sum(B[k].values())
        if na < 10 or nb < 10: continue
        acc += sum(min(A[k].get(x, 0)/na, B[k].get(x, 0)/nb) for x in set(A[k]) | set(B[k])) * (na + nb)
        tot += na + nb
    return acc / tot if tot else np.nan
st["own_ov"] = [overlap(p) for p in st.index]
st["eco_ov"] = [eco_overlap(d, p) for p in st.index]
st["group"] = [grp[p] for p in st.index]
st["gain"] = [float(pl.set_index("id").gain[p]) for p in st.index]
print("=== Repertoire stability (1 = identical choices both Septembers)")
for c, lab in (("eco_ov", "ECO of the whole game (opponent's choices included)"),
               ("own_ov", "own choices only: 1st move as White, reply to 1.e4 / 1.d4")):
    print(f"  {lab}")
    for gname in ("improver", "control"):
        print(f"    {gname:8s} mean {st[st.group==gname][c].mean():.3f}  median {st[st.group==gname][c].median():.3f}")
pr = pl.pivot(index="pair", columns="group", values="id")
diff = st.loc[pr.improver, "own_ov"].to_numpy() - st.loc[pr.control, "own_ov"].to_numpy()
rng = np.random.default_rng(23)
o, p, ci, n = signflip(diff, rng)
print(f"  own-choice overlap, improver minus control: {o:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] p = {p:.3f} n = {n}")
print("\n=== Does changing one's own openings go with improving OUTSIDE the opening?")
from scipy.stats import spearmanr
for gname in ("improver", "control", None):
    s = st if gname is None else st[st.group == gname]
    s = s.dropna(subset=["own_ov", "nonopen"])
    r1 = spearmanr(1 - s.own_ov, s.nonopen); r2 = spearmanr(1 - s.own_ov, s["I_Opening"])
    r3 = spearmanr(1 - s.own_ov, s.gain)
    print(f"  {gname or 'all 80':8s} n={len(s)}  change vs non-opening improvement rho {r1.correlation:+.2f} (p {r1.pvalue:.2f})"
          f" | vs opening improvement {r2.correlation:+.2f} (p {r2.pvalue:.2f})"
          f" | vs rating gain {r3.correlation:+.2f} (p {r3.pvalue:.2f})")
print("\n=== Did improvers improve outside the opening at all? (excess, log-odds)")
o, p, ci, n = signflip(st.loc[pr.improver, "nonopen"].to_numpy() - st.loc[pr.control, "nonopen"].to_numpy(), rng)
print(f"  non-opening mean excess {o:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] p = {p:.4f}")
