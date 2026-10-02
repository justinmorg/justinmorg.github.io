#!/usr/bin/env python3
"""
depthlabel_analyze.py — implements `depthlabel_prespec.md` exactly.

    python3 depthlabel_analyze.py moves.csv.gz depthlabel.jsonl[.gz]

Gates G1/G2 first; the primary test prints only if both pass. Every threshold
here is copied from the prespec — if they ever disagree, the prespec wins and
this file is the bug.
"""
import gzip
import hashlib
import json
import random
import sys

import numpy as np
import pandas as pd

DEPTHS = (1, 2, 4, 8, 12)
SEED = 20261002
NPERM = 4000
NBOOT = 2000


def load(moves_path, jl_path):
    m = pd.read_csv(moves_path, low_memory=False)
    m = m[(m.fullmove > 12) & (m.mate_flag == 0) & (m.spend >= 0)
          & (m.spend <= 60) & (m.drop_cp >= 200)].copy()
    op = gzip.open if jl_path.endswith(".gz") else open
    with op(jl_path, "rt") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    d = pd.DataFrame(rows)
    df = m.merge(d, on=["gid", "ply"], how="inner", validate="one_to_one")
    return m, df


def detect(r):
    for d in DEPTHS:
        if r[f"loss{d}"] >= 200:
            return d
    return None


def nonmono(r):
    seen = False
    for d in DEPTHS:
        hit = r[f"loss{d}"] >= 200
        if seen and not hit:
            return True
        seen = seen or hit
    return False


def cls(d):
    return "shallow" if d <= 2 else ("mid" if d == 4 else "deep")


def strata(df):
    q = pd.qcut(df.n_legal, 4, labels=False, duplicates="drop")
    caps = pd.cut(df.n_caps_avail, [-1, 0, 2, 99], labels=["0", "1-2", "3+"])
    band = np.where(df.fullmove <= 25, "13-25", "26+")
    return (df.tc.astype(str) + "|" + band + "|" + q.astype(str) + "|"
            + caps.astype(str) + "|" + df.in_check.astype(str))


def _codes(s):
    return pd.factorize(pd.Series(s))[0]


def std_diff(y, fast, s, w=None):
    """Directly standardized fast - slow difference in mean(y).

    Weights = pooled stratum size; strata lacking either group are dropped.
    `w` is an optional per-row multiplicity (game bootstrap)."""
    y = np.asarray(y, float)
    f = np.asarray(fast, bool)
    k = s if isinstance(s, np.ndarray) and s.dtype.kind == "i" else _codes(s)
    w = np.ones(len(y)) if w is None else w
    m = k.max() + 1
    nf = np.bincount(k[f], w[f], m)
    ns = np.bincount(k[~f], w[~f], m)
    sf = np.bincount(k[f], (w * y)[f], m)
    ss = np.bincount(k[~f], (w * y)[~f], m)
    ok = (nf > 0) & (ns > 0)
    wt = nf[ok] + ns[ok]
    d = ((sf[ok] / nf[ok] - ss[ok] / ns[ok]) * wt).sum() / wt.sum()
    return d, int(ok.sum())


def perm_p(y, fast, s, obs, rng):
    k = _codes(s)
    fast = np.asarray(fast, bool)
    order = np.argsort(k, kind="stable")
    bounds = np.flatnonzero(np.diff(k[order])) + 1
    groups = np.split(order, bounds)
    ge = 0
    for _ in range(NPERM):
        f2 = fast.copy()
        for gi in groups:
            f2[gi] = rng.permutation(fast[gi])
        d, _ = std_diff(y, f2, k)
        if abs(d) >= abs(obs) - 1e-12:
            ge += 1
    return (ge + 1) / (NPERM + 1)


def boot_ci(df, rng):
    g = _codes(df.gid)
    k = _codes(df.stratum)
    ng = g.max() + 1
    vals = []
    for _ in range(NBOOT):
        mult = np.bincount(rng.integers(0, ng, ng), minlength=ng).astype(float)
        d, _ = std_diff(df.shallow.values, df.fast.values, k, mult[g])
        vals.append(d)
    return np.percentile(vals, [2.5, 97.5])


def half(gid):
    h = hashlib.sha256(f"{SEED}:{gid}".encode()).digest()
    return "A" if h[0] % 2 == 0 else "B"


def pct(x):
    return f"{100 * x:.1f}%"


def main(moves_path, jl_path):
    pop, df = load(moves_path, jl_path)
    print(f"population {len(pop)}, labelled {len(df)}")
    if len(df) < len(pop):
        print("  NOTE: labelling incomplete — results below are a partial run")

    df["detect"] = df.apply(detect, axis=1)
    df["confirmed"] = df.loss12 >= 200
    conf_rate = df.confirmed.mean()
    print(f"\nG1 confirmed at depth 12: {df.confirmed.sum()}/{len(df)} = "
          f"{pct(conf_rate)}  (gate >= 75%) -> "
          f"{'PASS' if conf_rate >= 0.75 else 'FAIL'}")
    c = df[df.confirmed].copy()
    c["cls"] = c.detect.map(cls)
    c["shallow"] = (c.cls == "shallow").astype(float)
    c["nonmono"] = c.apply(nonmono, axis=1)

    h = c[c.hang_label != "none"]
    g2 = (h.cls == "shallow").mean()
    print(f"G2 SEE-flagged blunders classed shallow: "
          f"{(h.cls == 'shallow').sum()}/{len(h)} = {pct(g2)}  (gate >= 85%) -> "
          f"{'PASS' if g2 >= 0.85 else 'FAIL'}")
    print("   by hang_label:")
    for lbl, x in h.groupby("hang_label"):
        print(f"     {lbl:22s} n={len(x):5d}  shallow {pct((x.cls == 'shallow').mean())}")
    if conf_rate < 0.75 or g2 < 0.85:
        print("\nGATE FAILED — primary test not interpreted.")
        return

    print("\nS3 counts")
    print(f"   unconfirmed {(~df.confirmed).sum()}, non-monotone among confirmed "
          f"{c.nonmono.sum()} ({pct(c.nonmono.mean())})")
    print("   detect depth, all confirmed:",
          c.detect.value_counts().sort_index().to_dict())
    print("   class by format:")
    print(pd.crosstab(c.tc, c.cls, normalize="index").round(3).to_string())

    rng = np.random.default_rng(SEED)
    fs = c[(c.spend <= 2) | (c.spend >= 8)].copy()
    fs["fast"] = fs.spend <= 2
    fs["stratum"] = strata(fs).values

    def report(sub, name):
        raw_f = sub[sub.fast].shallow.mean()
        raw_s = sub[~sub.fast].shallow.mean()
        d, k = std_diff(sub.shallow, sub.fast, sub.stratum)
        kept = sub.groupby("stratum").fast.nunique()
        dropped = sub.stratum.isin(kept[kept < 2].index).sum()
        p = perm_p(sub.shallow.values, sub.fast.values, sub.stratum.values, d, rng)
        lo, hi = boot_ci(sub, rng)
        print(f"\n{name}")
        print(f"   n fast {int(sub.fast.sum())}, slow {int((~sub.fast).sum())}; "
              f"strata used {k}, rows in dropped strata {dropped}")
        print(f"   shallow share raw: fast {pct(raw_f)}  slow {pct(raw_s)}  "
              f"diff {100 * (raw_f - raw_s):+.2f} pp")
        print(f"   standardized fast - slow: {100 * d:+.2f} pp "
              f"[{100 * lo:+.2f}, {100 * hi:+.2f}]  perm p = {p:.4f}")
        for hv in ("A", "B"):
            x = sub[sub.gid.map(half) == hv]
            dh, _ = std_diff(x.shallow, x.fast, x.stratum)
            print(f"   half {hv}: n {len(x)}  standardized {100 * dh:+.2f} pp")
        print("   class mix fast vs slow:")
        print(pd.crosstab(sub.fast.map({True: "fast", False: "slow"}), sub.cls,
                          normalize="index").round(3).to_string())
        return d, p

    report(fs, "PRIMARY — all confirmed blunders, fast (<=2s) vs slow (>=8s)")
    report(fs[fs.hang_label == "none"], "S1 — hang_label == none only")

    print("\nS2 — class mix by spend band (unstandardized)")
    bands = [(-0.01, 0, "0"), (0, 1, "0-1"), (1, 2, "1-2"), (2, 4, "2-4"),
             (4, 8, "4-8"), (8, 16, "8-16"), (16, 60, "16+")]
    for lo, hi, nm in bands:
        x = c[(c.spend > lo) & (c.spend <= hi)]
        mix = x.cls.value_counts(normalize=True)
        print(f"   {nm:5s} n={len(x):5d}  shallow {pct(mix.get('shallow', 0))}  "
              f"mid {pct(mix.get('mid', 0))}  deep {pct(mix.get('deep', 0))}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
