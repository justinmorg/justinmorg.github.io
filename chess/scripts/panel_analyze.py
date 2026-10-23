#!/usr/bin/env python3
"""Thread 9, step 5: the improvers-vs-controls test. Implements
panel_prespec.md exactly; if anything here disagrees with that file, this
file is wrong.

    # features + mate scan over annotated player-months (resumable):
    python3 panel_analyze.py prep  /home/claude/panel --pairs 1-40
    # the test itself:
    python3 panel_analyze.py test  /home/claude/panel --pairs 1-40 [--look 1|2]

prep writes <dir>/feat/ (features.py, one block per player-month, labelled
<id>_<yymm>, user = id) and <dir>/feat/matedanger.csv.

test reads those plus <dir>/panel_ranks_private.csv (for the Sep 2025 mean
rating the panel was selected on) and the anonymised PGNs (for ECO), and
prints every pre-specified quantity. It refuses to run unless every
player-month of the requested pairs is annotated.
"""
import csv, os, subprocess, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from buckets import assign, MATE_CP  # noqa: E402

AREAS = ["Opening", "MG level", "MG winning", "EG ahead", "EG level", "M2 mate danger"]
MIN_MOVES, MIN_AREAS = 100, 5
ALPHA = 0.029           # Pocock, two looks
DELTA = 0.5
SEED, DRAWS, BOOT = 23, 20000, 2000


def args():
    a = sys.argv[1:]
    mode, d = a[0], a[1]
    lo, hi = map(int, a[a.index("--pairs") + 1].split("-"))
    look = int(a[a.index("--look") + 1]) if "--look" in a else 1
    return mode, d, lo, hi, look


def manifest(d, lo, hi):
    man = pd.read_csv(os.path.join(d, "pm", "manifest.csv"), dtype={"month": str})
    return man[(man.pair >= lo) & (man.pair <= hi)]


def prep(d, lo, hi):
    man = manifest(d, lo, hi)
    done = set(open(os.path.join(d, "ann", "done.txt")).read().split())
    pms = [f"{r.id}_{r.month}" for r in man.itertuples()]
    missing = [p for p in pms if p not in done]
    if missing:
        sys.exit(f"{len(missing)} player-months not annotated yet, e.g. {missing[:3]}")
    out = os.path.join(d, "feat")
    cmd = [sys.executable, os.path.join(HERE, "features.py")]
    cmd += [f"{p}={os.path.join(d, 'ann', p + '_analyzed.pgn')}" for p in pms]
    cmd += ["--tc", "180+2,300+0", "--emit-fens", "all", "--out", out, "--user-map"]
    cmd += [f"{p}={p.split('_')[0]}" for p in pms]
    subprocess.run(cmd, check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "matedanger.py"), out,
                    os.path.join(out, "matedanger.csv"), "--workers", "2"], check=True)


def logit(e, n):
    r = (e + 0.5) / (n + 1)
    return np.log(r / (1 - r))


def eco_overlap(d, pid):
    """Frequency-weighted overlap of ECO codes between months, per colour."""
    def dist(yymm):
        c = {"w": {}, "b": {}}
        txt = open(os.path.join(d, "pm", f"{pid}_{yymm}.pgn")).read()
        for g in txt.split("[Event ")[1:]:
            w = g.split('[White "', 1)[1].split('"', 1)[0]
            eco = g.split('[ECO "', 1)[1].split('"', 1)[0] if '[ECO "' in g else "?"
            col = "w" if w == pid else "b"
            c[col][eco] = c[col].get(eco, 0) + 1
        return c
    a, b = dist("2509"), dist("2609")
    tot, acc = 0, 0.0
    for col in "wb":
        na, nb = sum(a[col].values()), sum(b[col].values())
        if not na or not nb: continue
        ov = sum(min(a[col].get(k, 0) / na, b[col].get(k, 0) / nb)
                 for k in set(a[col]) | set(b[col]))
        acc += ov * (na + nb); tot += na + nb
    return acc / tot if tot else np.nan


def player_tables(d, lo, hi, tc_filter=None):
    feat = os.path.join(d, "feat")
    m = pd.read_csv(os.path.join(feat, "moves.csv.gz"), dtype={"block": str, "gid": str})
    g = pd.read_csv(os.path.join(feat, "games.csv"), dtype={"block": str, "gid": str})
    md = pd.read_csv(os.path.join(feat, "matedanger.csv"), dtype={"gid": str})
    # A game where two panel players met appears in two blocks with the same
    # gid; matedanger rows are per (gid, ply) and the ply sets differ by colour,
    # so the merge is still one-to-one per own move.
    m = m.merge(md.drop_duplicates(["gid", "ply"]), on=["gid", "ply"], how="left")
    need = m.cp_before.abs() < MATE_CP
    if m.loc[need, "a_null"].isna().any():
        sys.exit("GATE: positions missing from the mate scan")
    if tc_filter:
        m = m[m.tc == tc_filter]; g = g[g.tc == tc_filter]
    m["bucket"] = assign(m)
    m["e15"] = (m.wp_error >= 0.15).astype(float)
    m["pid"] = m.block.str.split("_").str[0]
    m["month"] = m.block.str.split("_").str[1]
    # half A / B by game order within Sep 2025 (files are time-sorted and
    # features.py keeps file order)
    g = g.copy()
    g["order"] = g.groupby("block").cumcount()
    g["half"] = np.where(g.order % 2 == 0, "A", "B")    # 1st, 3rd, ... = odd = A
    m = m.merge(g[["block", "gid", "half"]], on=["block", "gid"], how="left")
    m.loc[m.month == "2609", "half"] = "S26"
    m = m[m.bucket.isin(AREAS)]
    t = m.groupby(["pid", "half", "bucket"]).e15.agg(["sum", "count"]).reset_index()
    return t, m


def per_player(t, rating, pids):
    """Cross-fitted per-player statistics. Returns DataFrame indexed by pid."""
    E = t.pivot_table(index=["pid", "bucket"], columns="half", values="sum").reindex(
        pd.MultiIndex.from_product([pids, AREAS], names=["pid", "bucket"]))
    N = t.pivot_table(index=["pid", "bucket"], columns="half", values="count").reindex(
        E.index)
    E = E.reindex(columns=["A", "B", "S26"]).fillna(0)
    N = N.reindex(columns=["A", "B", "S26"]).fillna(0)
    counts = (N >= MIN_MOVES).all(axis=1)
    L = pd.DataFrame({h: logit(E[h], N[h]) for h in ["A", "B", "S26"]})
    L["count"] = counts
    L["rating"] = [rating[p] for p, _ in L.index]
    n_areas = counts.groupby(level=0).sum()
    ok = n_areas[n_areas >= MIN_AREAS].index
    res = {}
    for prof, meas in (("A", "B"), ("B", "A")):
        # rating-expected profile per area, WLS across panel players who count it
        R = pd.Series(np.nan, index=L.index)
        for a in AREAS:
            sel = [(p, a) for p in ok if L.loc[(p, a), "count"]]
            x = np.array([L.loc[s, "rating"] for s in sel])
            y = np.array([L.loc[s, prof] for s in sel])
            w = np.array([N.loc[s, prof] for s in sel])
            X = np.c_[np.ones_like(x), x]
            beta = np.linalg.lstsq(X * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
            for s, xi, yi in zip(sel, x, y):
                R[s] = yi - (beta[0] + beta[1] * xi)
        I = L[meas] - L["S26"]
        for p in ok:
            ar = [a for a in AREAS if L.loc[(p, a), "count"]]
            r = np.array([R[(p, a)] for a in ar]); i = np.array([I[(p, a)] for a in ar])
            b = np.polyfit(r, i, 1)[0]
            best, worst = ar[int(np.argmin(r))], ar[int(np.argmax(r))]
            row = res.setdefault(p, {"beta": [], "C": [], "I_all": [],
                                      **{f"I_{a}": [] for a in AREAS}, "R_open": []})
            row["beta"].append(b)
            row["C"].append(I[(p, worst)] - I[(p, best)])
            row["I_all"].append(i.mean())
            for a in AREAS:
                row[f"I_{a}"].append(I[(p, a)] if L.loc[(p, a), "count"] else np.nan)
            row["R_open"].append(R[(p, "Opening")] if L.loc[(p, "Opening"), "count"] else np.nan)
    out = pd.DataFrame({p: {k: np.nanmean(v) if not all(np.isnan(v)) else np.nan
                            for k, v in r.items()} for p, r in res.items()}).T
    out["n_areas"] = n_areas.reindex(out.index)
    return out, n_areas


def signflip(diff, rng):
    diff = np.asarray(diff, float); diff = diff[np.isfinite(diff)]
    if len(diff) == 0: return np.nan, np.nan, (np.nan, np.nan), 0
    obs = diff.mean()
    signs = rng.choice([-1.0, 1.0], size=(DRAWS, len(diff)))
    null = (signs * diff).mean(1)
    p = (np.sum(np.abs(null) >= abs(obs)) + 1) / (DRAWS + 1)
    br = np.random.default_rng(SEED)
    boots = diff[br.integers(0, len(diff), (BOOT, len(diff)))].mean(1)
    return obs, p, tuple(np.percentile(boots, [2.5, 97.5])), len(diff)


def test(d, lo, hi, look):
    alpha = ALPHA
    man = manifest(d, lo, hi)
    ranks = pd.read_csv(os.path.join(d, "panel_ranks_private.csv"))
    rating = dict(zip(ranks.id, ranks.mean_2509))
    pairs = ranks[(ranks.pair >= lo) & (ranks.pair <= hi)]
    pids = list(pairs.id)
    t, m = player_tables(d, lo, hi)
    st, n_areas = per_player(t, rating, pids)

    # pair-level eligibility (area rule): both members need >= 5 counting areas
    pr = pairs.pivot(index="pair", columns="group", values="id")
    pr["ok"] = [(i in st.index) and (c in st.index) for i, c in zip(pr.improver, pr.control)]
    failed = pr[~pr.ok]
    print(f"pairs examined {len(pr)}, failing the area rule {len(failed)}")
    for k, r in failed.iterrows():
        print(f"  pair {k}: improver areas {int(n_areas.get(r.improver, 0))}, "
              f"control areas {int(n_areas.get(r.control, 0))}")
    if len(failed) > len(pr) / 2:
        sys.exit("STOP: more than half the pairs fail the area rule -- decision needed")
    target = 40 * look
    use = pr[pr.ok].sort_index().head(target)    # first passing pairs in rank order
    print(f"pairs in the test: {len(use)} (target {target})"
          + ("" if len(use) >= target else
             "  -- SHORT: annotate the next ranks as replacements, then rerun"))

    def excess(col, sub=None):
        u = use if sub is None else use.loc[sub]
        return st.loc[u.improver, col].to_numpy() - st.loc[u.control, col].to_numpy()

    rng = np.random.default_rng(SEED)
    res = {k: signflip(excess(k), rng) for k in ["I_all", "beta", "C"]}
    for k, (o, p, ci, n) in res.items():
        print(f"excess {k:6s} = {o:+.3f}  95% [{ci[0]:+.3f}, {ci[1]:+.3f}]  p = {p:.4f}  (n = {n})")

    # decision rule
    gI, gb, gC = res["I_all"], res["beta"], res["C"]
    per_area = {a: signflip(excess(f"I_{a}"), rng) for a in AREAS}
    if not (gI[0] > 0 and gI[1] < alpha):
        verdict = "GATE FAILED: rating gain not visible in error rates"
    elif np.sign(gb[0]) != np.sign(gC[0]):          # "regardless of p"
        verdict = "UNRESOLVED (beta and C disagree in sign)"
    elif gb[0] > 0 and gb[1] < alpha and gC[0] > 0:
        verdict = "H-weakness"
    elif gb[0] < 0 and gb[1] < alpha and gC[0] < 0:
        verdict = "H-strength"
    elif gb[1] >= alpha and -DELTA <= gb[2][0] and gb[2][1] <= DELTA and \
            sum(per_area[a][0] > 0 for a in AREAS) >= 4:
        verdict = "H-all"
    else:
        verdict = "UNRESOLVED"
    print(f"\nVERDICT (look {look}, alpha {alpha}): {verdict}")

    print("\nsecondary: per-area excess I_a (Holm across six)")
    ps = sorted((per_area[a][1], a) for a in AREAS)
    holm = {}
    run = 0.0
    for i, (p, a) in enumerate(ps):
        run = max(run, min(1.0, p * (len(AREAS) - i))); holm[a] = run
    for a in AREAS:
        o, p, ci, n = per_area[a]
        print(f"  {a:15s} {o:+.3f}  [{ci[0]:+.3f}, {ci[1]:+.3f}]  p = {p:.4f}  Holm {holm[a]:.3f}  n = {n}")

    print("\nsecondary: composition (mean cp_before, move share %), by group and month")
    grp = dict(zip(ranks.id, ranks.group))
    mm = m[m.pid.isin(set(use.improver) | set(use.control))].copy()
    mm["group"] = mm.pid.map(grp)
    comp = mm[mm.cp_before.abs() < MATE_CP].pivot_table(
        index="bucket", columns=["group", "month"], values="cp_before", aggfunc="mean")
    print(comp.reindex(AREAS).round(0).to_string())

    print("\nsecondary: 3+2-only robustness (beta excess must share the sign)")
    t32, _ = player_tables(d, lo, hi, tc_filter="180+2")
    st32, _ = per_player(t32, rating, pids)
    ok32 = [k for k, r in use.iterrows() if r.improver in st32.index and r.control in st32.index]
    if ok32:
        u32 = use.loc[ok32]
        o, p, ci, n = signflip(st32.loc[u32.improver, "beta"].to_numpy()
                               - st32.loc[u32.control, "beta"].to_numpy(), rng)
        print(f"  beta excess {o:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] p = {p:.4f} n = {n}; "
              f"sign {'agrees' if np.sign(o) == np.sign(gb[0]) else 'DISAGREES'}")

    print("\nsecondary: repertoire change")
    ov = {p: eco_overlap(d, p) for p in set(use.improver) | set(use.control)}
    oi = np.array([ov[p] for p in use.improver]); oc = np.array([ov[p] for p in use.control])
    print(f"  ECO overlap, mean: improvers {np.nanmean(oi):.3f}, controls {np.nanmean(oc):.3f}")
    cut = np.nanpercentile(list(ov.values()), 20)
    keep = [k for k, r in use.iterrows() if ov[r.improver] > cut and ov[r.control] > cut]
    o, p, ci, n = signflip(excess("beta", keep), rng)
    print(f"  sensitivity, dropping pairs with either overlap <= {cut:.3f} (bottom 20%): "
          f"beta excess {o:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}] p = {p:.4f} n = {n}")
    ro = st.loc[list(use.improver) + list(use.control), "R_open"].dropna()
    top = ro[ro >= ro.quantile(0.9)].sort_values(ascending=False)
    print("  Sep 2025 opening R in the panel's top 10% (look up with the key file):")
    for p, v in top.items():
        print(f"    {p} ({grp[p]})  R_open {v:+.2f}  overlap {ov[p]:.3f}")

    print("\nhazard listing: improvers whose Sep 2026 P1 rate is below the panel's "
          "minimum in every counting area")
    s26 = t[t.half == "S26"].assign(rate=lambda x: x["sum"] / x["count"])
    s26 = s26[s26.pid.isin(set(use.improver) | set(use.control))]
    mins = s26.groupby("bucket").rate.min()
    flag = [p for p in use.improver
            if all(r.rate <= mins[r.bucket] for r in s26[s26.pid == p].itertuples())]
    print("  " + (", ".join(flag) if flag else "none"))


if __name__ == "__main__":
    mode, d, lo, hi, look = args()
    {"prep": lambda: prep(d, lo, hi), "test": lambda: test(d, lo, hi, look)}[mode]()
