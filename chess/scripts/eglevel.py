#!/usr/bin/env python3
"""Block homogeneity of the level-endgame score. Pre-specified in
eglevel_prespec.md — read that first; this file implements it and nothing
else decides.

Usage:
    python3 eglevel.py [features_dir]      # the EIGHT-block features.py run

Population: games whose endgame-entry eval is level, using features.py's
`eg_entry_cp` (entry checked on every ply) and outcomes.bucket_of imported,
not restated. Unit = game; label = block.

Three things are printed, in this order:
  1. gates (hard-exit) — the seven published blocks must reproduce
     5,404 games, endgame-entry 1,073 / 401 / 774 / 1,443, level 42.7%,
     the site split 641 / 133 and the Lichess format split 529 / 112.
  2. the homogeneity test on the seven blocks — spread p decides
     (blockstats.py's scheme, 20,000 draws, seed 23); min/max-block p
     are printed for completeness and do not decide.
  3. Q4-2025 as the held-out replication block — two-sided single-block
     permutation against the pooled seven, plus the resolution both tests
     actually have at these n, by simulation.

The per-block entry-ply split at the end is descriptive only (the selection
caveat in the pre-spec) and is not part of any rule.
"""
import os
import random
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outcomes import bucket_of  # noqa: E402

FEAT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
SEVEN = ["2024H2", "Q1-2025", "Q2-2025", "Q3-2025", "2026", "CC-2024Q4", "CC-2026"]
HELD_OUT = "Q4-2025"
LEVEL = "level (-100..+100)"
N_PERM, SEED = 20000, 23


def block_rates(labels, scores):
    a = {}
    for lab, s in zip(labels, scores):
        t = a.setdefault(lab, [0, 0.0])
        t[0] += 1
        t[1] += s
    return {k: 100.0 * v[1] / v[0] for k, v in a.items()}


def shuffle_test(labels, scores, n=N_PERM, seed=SEED):
    """blockstats.py cmd_shuffle, re-implemented on (label, score) pairs."""
    obs = block_rates(labels, scores)
    spread = max(obs.values()) - min(obs.values())
    lo, hi = min(obs.values()), max(obs.values())
    rng = random.Random(seed)
    work = list(labels)
    c_spread = c_min = c_max = 0
    for _ in range(n):
        rng.shuffle(work)
        r = block_rates(work, scores)
        if max(r.values()) - min(r.values()) >= spread:
            c_spread += 1
        if min(r.values()) <= lo:
            c_min += 1
        if max(r.values()) >= hi:
            c_max += 1
    return obs, spread, ((c_spread + 1) / (n + 1), (c_min + 1) / (n + 1),
                         (c_max + 1) / (n + 1))


def two_sided_block(is_q, scores, n=N_PERM, seed=SEED):
    """|rate(Q) - rate(rest)| under game-level shuffles of the Q label."""
    is_q = np.asarray(is_q, bool)
    s = np.asarray(scores, float)
    obs = s[is_q].mean() - s[~is_q].mean()
    rng = np.random.default_rng(seed)
    c = 0
    for _ in range(n):
        p = rng.permutation(is_q)
        if abs(s[p].mean() - s[~p].mean()) >= abs(obs):
            c += 1
    return obs, (c + 1) / (n + 1)


def _spread_p(idx, k, scores, n_perm, rng):
    """Spread-statistic permutation p, vectorised: permuting scores over a
    fixed label vector is the same test as permuting labels."""
    obs = np.bincount(idx, weights=scores, minlength=len(k)) / k
    spread = obs.max() - obs.min()
    c = 0
    for _ in range(n_perm):
        r = np.bincount(idx, weights=rng.permutation(scores), minlength=len(k)) / k
        if r.max() - r.min() >= spread:
            c += 1
    return (c + 1) / (n_perm + 1)


def resolution_spread(sizes, base, n_sim=300, n_perm=300, seed=SEED):
    """Smallest one-block shift delta (that block at base+delta, others at
    base) the spread test rejects at alpha 0.05 in >= 80% of simulations,
    for the smallest and the largest block. Coarse (0.02 grid) by design.
    Scores are drawn Bernoulli on the mean — slightly more dispersed than a
    {0, 0.5, 1} outcome, so the stated resolution is conservative."""
    rng = np.random.default_rng(seed)
    names = list(sizes)
    k = np.array([sizes[b] for b in names], float)
    idx = np.repeat(np.arange(len(names)), k.astype(int))
    out = {}
    for which in ("smallest", "largest"):
        name = (min if which == "smallest" else max)(sizes, key=sizes.get)
        j = names.index(name)
        found = None
        for delta in np.arange(0.02, 0.62, 0.02):
            p = np.full(len(idx), base)
            p[idx == j] = min(1.0, base + delta)
            rej = 0
            for _ in range(n_sim):
                scores = (rng.random(len(idx)) < p).astype(float)
                if _spread_p(idx, k, scores, n_perm, rng) < 0.05:
                    rej += 1
            if rej / n_sim >= 0.80:
                found = delta
                break
        out[which] = (name, sizes[name], found)
    return out


def resolution_q(n_q, base, alpha=0.05, power=0.80):
    from math import sqrt
    z_a, z_b = 1.95996, 0.84162
    return (z_a + z_b) * sqrt(base * (1 - base) / n_q)


def main():
    g = pd.read_csv(os.path.join(FEAT, "games.csv"),
                    dtype={"block": str, "gid": str})
    with pd.option_context("mode.chained_assignment", None):
        n_rows = sum(len(c) for c in pd.read_csv(
            os.path.join(FEAT, "moves.csv.gz"), usecols=["gid"],
            dtype={"gid": str}, chunksize=200000))

    # ---- gate 1: eight-block run ------------------------------------------
    if len(g) != 5636 or n_rows != 186191:
        sys.exit(f"ERROR: expected the eight-block run (5,636 games / 186,191 "
                 f"rows), got {len(g)} / {n_rows}.")
    if HELD_OUT not in set(g.block):
        sys.exit(f"ERROR: block {HELD_OUT!r} missing from games.csv")

    eg = g[g.eg_entry_cp.notna()].copy()
    eg["eg_bucket"] = eg.eg_entry_cp.apply(bucket_of)
    lvl = eg[eg.eg_bucket == LEVEL].copy()

    # ---- gate 2: the seven published blocks reproduce ---------------------
    g7 = g[g.block.isin(SEVEN)]
    eg7 = eg[eg.block.isin(SEVEN)]
    counts = eg7.eg_bucket.value_counts().to_dict()
    want = {"winning (>+300)": 1073, "ahead (+100..+300)": 401,
            LEVEL: 774, "losing (<-100)": 1443}
    lvl7 = lvl[lvl.block.isin(SEVEN)]
    rate7 = 100.0 * lvl7.score.mean()
    if len(g7) != 5404 or counts != want or round(rate7, 1) != 42.7:
        sys.exit(f"ERROR: seven-block subset does not reproduce: {len(g7)} "
                 f"games, buckets {counts}, level {rate7:.2f}%")
    # ---- gate 3: site split ------------------------------------------------
    li, cc = lvl7[lvl7.site == "lichess"], lvl7[lvl7.site == "chesscom"]
    if (len(li), round(100 * li.score.mean(), 1)) != (641, 43.1) or \
       (len(cc), round(100 * cc.score.mean(), 1)) != (133, 41.0):
        sys.exit(f"ERROR: site split {len(li)}/{100*li.score.mean():.1f} "
                 f"{len(cc)}/{100*cc.score.mean():.1f} != 641/43.1 133/41.0")
    # ---- gate 4: Lichess format split -------------------------------------
    a, b = li[li.tc == "180+2"], li[li.tc == "300+0"]
    if (len(a), round(100 * a.score.mean(), 1)) != (529, 42.1) or \
       (len(b), round(100 * b.score.mean(), 1)) != (112, 47.8):
        sys.exit(f"ERROR: format split {len(a)}/{100*a.score.mean():.1f} "
                 f"{len(b)}/{100*b.score.mean():.1f} != 529/42.1 112/47.8")
    print(f"gates OK: eight-block run; seven blocks -> 5,404 games, endgame "
          f"entry 1,073 / 401 / 774 / 1,443, level {rate7:.1f}%, "
          f"site 641/133, format 529/112\n")

    # ---- 2. homogeneity, seven blocks --------------------------------------
    labels = list(lvl7.block)
    scores = list(lvl7.score.astype(float))
    obs, spread, (p_s, p_min, p_max) = shuffle_test(labels, scores)
    sizes = lvl7.block.value_counts().to_dict()
    print("level-endgame score by block (seven blocks, %d games)\n" % len(lvl7))
    print("%-10s %6s %8s" % ("block", "games", "score%"))
    for b in SEVEN:
        print("%-10s %6d %8.1f" % (b, sizes[b], obs[b]))
    lo_b = min(obs, key=obs.get)
    hi_b = max(obs, key=obs.get)
    print("\n%d shuffles, seed %d" % (N_PERM, SEED))
    print("  spread %.1f pp across blocks         p = %.4f   <-- decides" % (spread, p_s))
    print("  minimum block (%s, %.1f%%)   p = %.4f   (reported, does not decide)"
          % (lo_b, obs[lo_b], p_min))
    print("  maximum block (%s, %.1f%%)   p = %.4f   (reported, does not decide)"
          % (hi_b, obs[hi_b], p_max))
    verdict = "BLOCKS DIFFER (flag)" if p_s < 0.05 else "no block differs"
    print("  verdict on the pre-specified rule (spread p < 0.05): %s" % verdict)

    # secondary, Lichess-only five blocks — descriptive robustness
    li5 = lvl7[lvl7.site == "lichess"]
    o5, sp5, (p5, _, _) = shuffle_test(list(li5.block), list(li5.score.astype(float)))
    print("\n  Lichess-only five blocks: spread %.1f pp, p = %.4f  (secondary, "
          "does not decide)" % (sp5, p5))

    # ---- 3. Q4-2025 held out -------------------------------------------------
    lq = lvl[lvl.block == HELD_OUT]
    pool = pd.concat([lvl7, lq])
    is_q = (pool.block == HELD_OUT).values
    d, p_q = two_sided_block(is_q, pool.score.astype(float).values)
    print("\n%s held out: %d level-endgame games of %d, score %.1f%%  "
          "(pooled seven: %.1f%%)" % (HELD_OUT, len(lq),
                                       int((g.block == HELD_OUT).sum()),
                                       100 * lq.score.mean(), rate7))
    print("  Q4 - pooled = %+.1f pp, two-sided game-level p = %.4f" % (100 * d, p_q))
    print("  verdict on the pre-specified rule (p >= 0.05 replicates): %s"
          % ("replicates" if p_q >= 0.05 else "FAILS replication (flag)"))
    print("  W/D/L in Q4 level endgames: %d/%d/%d"
          % ((lq.score == 1).sum(), (lq.score == 0.5).sum(), (lq.score == 0).sum()))

    # ---- resolution --------------------------------------------------------
    base = rate7 / 100.0
    rq = resolution_q(len(lq), base)
    print("\nresolution")
    print("  Q4 replication: 80%% power at alpha 0.05 detects |delta| >= %.1f pp "
          "on %d games (i.e. %.1f%% -> below %.1f%% or above %.1f%%)"
          % (100 * rq, len(lq), rate7, rate7 - 100 * rq, rate7 + 100 * rq))
    print("  spread test, simulated at the actual block sizes (one block shifted, "
          "rest at %.1f%%):" % rate7)
    res = resolution_spread(sizes, base)
    for which, (name, k, delta) in res.items():
        print("    %s block (%s, n=%d): detects a shift of about %s"
              % (which, name, k, ("%.0f pp" % (100 * delta)) if delta else ">60 pp"))

    # ---- descriptive: entry ply split (selection caveat) -------------------
    print("\nentry-ply split, descriptive only (selection caveat in the pre-spec)")
    print("%-10s %8s %8s %8s %8s" % ("block", "n<=30", "score", "n>30", "score"))
    for b in SEVEN + [HELD_OUT]:
        s = lvl[lvl.block == b]
        e_ = s[s.eg_entry_ply <= 60]   # ply 60 = fullmove 30
        l_ = s[s.eg_entry_ply > 60]
        print("%-10s %8d %8.1f %8d %8.1f" % (
            b, len(e_), 100 * e_.score.mean() if len(e_) else float("nan"),
            len(l_), 100 * l_.score.mean() if len(l_) else float("nan")))
    q_early = 100.0 * (lvl[lvl.block == HELD_OUT].eg_entry_ply <= 26).mean()
    o_early = 100.0 * (lvl7.eg_entry_ply <= 26).mean()
    print("\n  share entering the endgame at fullmove 13 (early simplification): "
          "Q4 %.1f%% vs seven-block %.1f%%" % (q_early, o_early))


if __name__ == "__main__":
    main()
