#!/usr/bin/env python3
"""Do the standing-threat finding and the first-deterioration finding coincide?

Two results in the README describe "opponent-resource blindness":

  * standing threats are +6.28 pp more dangerous than newly created ones
    (see "Old threats are the dangerous ones")
  * level games are decided by a permanent first drop in the early middlegame
    (see "The first major deterioration")

They could be one event seen from two angles, or two distinct failure modes
whose loss budgets add. This script settles it at three levels: the same move,
the same game, and the loss budget.

Usage:
    python3 chess/scripts/firstdrop.py /home/claude/features   # produces the input
    python3 chess/scripts/coincide.py  /home/claude/features

Validation-gated on the features.py precedent — it hard-exits unless the input
is the 5,404-game / 178,684-row seven-block run and the published event counts
reproduce. Validate against a known number before trusting a new pipeline.
"""
import sys
import os
import numpy as np
import pandas as pd

N_PERM = 10_000
N_BOOT = 2_000
SEED = 23


def die(msg):
    sys.exit(f"FATAL: {msg}")


def load(d):
    m = pd.read_csv(os.path.join(d, "moves.csv.gz"),
                    dtype={"block": str, "gid": str})
    g = pd.read_csv(os.path.join(d, "games.csv"),
                    dtype={"block": str, "gid": str})
    fdp = os.path.join(d, "firstdrop", "firstdrop_200.csv")
    lgp = os.path.join(d, "firstdrop", "level_games.csv")
    if not (os.path.exists(fdp) and os.path.exists(lgp)):
        die("run firstdrop.py first — %s missing" % os.path.dirname(fdp))
    fd = pd.read_csv(fdp, dtype={"block": str, "gid": str})
    lg = pd.read_csv(lgp, dtype={"block": str, "gid": str})
    return m, g, fd, lg


def events(m, fd, lg):
    """A = permanent hot-zone first drop; B = standing-threat blunder;
    P = group P floored missed-their-threat hit."""
    lev = lg[lg.entry_bucket == "level"]
    fdl = fd[fd.gid.isin(set(lev.gid))]
    hot = fdl[(~fdl.rec5) & fdl.fullmove.between(13, 25) & (fdl.npm_light >= 13)]

    base = m[(m.fullmove > 12) & (m.mate_flag == 0)]
    stand = base[(base.see_standing >= 150) & (base.opp_created_threat == 0)]
    bmv = stand[stand.drop_cp >= 200]

    e = m[m.elig_P == 1]
    pmv = e[(e.hang_label == "missed_their_threat") & (e.wp_error >= 0.02)]
    return lev, hot, base, bmv, pmv


def gate(m, lev, hot, base, bmv):
    """Reproduce published figures or refuse to run."""
    if len(m) != 178_684 or m.gid.nunique() != 5_404:
        die("expected the 5,404-game / 178,684-row seven-block features run, "
            f"got {m.gid.nunique():,} / {len(m):,}")
    if len(base) != 108_151:
        die(f"oppmove scope should be 108,151 rows, got {len(base):,}")
    hangset = base[base.see_standing >= 150]
    ncre = int((hangset.opp_created_threat == 1).sum())
    nsta = int((hangset.opp_created_threat == 0).sum())
    if (ncre, nsta) != (19_486, 3_006):
        die(f"standing-threat arms should be 19,486 / 3,006, got {ncre:,} / {nsta:,}")
    rate = 100 * (hangset[hangset.opp_created_threat == 0].drop_cp >= 200).mean()
    if abs(rate - 16.73) > 0.05:
        die(f"standing-arm raw blunder rate should be 16.73%, got {rate:.2f}%")
    if len(lev) != 1_930:
        die(f"level-at-entry games should be 1,930, got {len(lev):,}")
    if len(hot) != 633:
        die(f"permanent hot-zone first drops should be 633, got {len(hot):,}")
    print(f"gates OK: {m.gid.nunique():,} games / {len(m):,} rows; "
          f"standing arms 19,486/3,006 @ 16.73%; level {len(lev):,}; hot zone {len(hot):,}")


def same_move(hot, bmv, pmv):
    print("\n--- 1. the same MOVE? ---")
    hk = set(zip(hot.gid, hot.ply))
    bk = set(zip(bmv.gid, bmv.ply))
    pk = set(zip(pmv.gid, pmv.ply))
    print(f"  hot-zone drops that are standing-threat blunders: "
          f"{len(hk & bk)}/{len(hk)} = {100 * len(hk & bk) / len(hk):.1f}%")
    print(f"  hot-zone drops that are group P floored hits    : "
          f"{len(hk & pk)}/{len(hk)} = {100 * len(hk & pk) / len(hk):.1f}%")
    s = hot.see_standing >= 150
    c = hot.opp_created_threat == 1
    print(f"\n  decomposition of the {len(hot)} hot-zone drops:")
    print(f"    no material hanging               {int((~s).sum()):4d} "
          f"({100 * (~s).mean():.0f}%)")
    print(f"    hanging, opponent JUST created it {int((s & c).sum()):4d}")
    print(f"    hanging, threat ALREADY standing  {int((s & ~c).sum()):4d}")
    print("  the hot zone's hanging-material minority is almost entirely FRESH")
    print("  threats — the arm oppmove.py found to be the safe one.")


def same_game(g, lev, hot, base, bmv, pmv):
    rng = np.random.default_rng(SEED)
    print("\n--- 2. the same GAME? (level-at-entry universe, exposure-matched) ---")
    u = g[g.gid.isin(set(lev.gid))][["gid", "score"]].copy()
    u["A"] = u.gid.isin(set(hot.gid)).astype(int)
    u["B"] = u.gid.isin(set(bmv.gid)).astype(int)
    u["P"] = u.gid.isin(set(pmv.gid)).astype(int)
    # exposure: own moves after move 12 — both events can only occur there, so a
    # long game has more chances at both and would fake co-occurrence.
    expo = base.groupby("gid").size().rename("n_mid")
    u = u.merge(expo, left_on="gid", right_index=True, how="left").fillna({"n_mid": 0})
    u["stratum"] = pd.qcut(u.n_mid, 5, labels=False, duplicates="drop")

    for col, name in [("B", "standing-threat blunder"), ("P", "group P floored hit")]:
        av, bv, st = u.A.values, u[col].values, u.stratum.values
        obs = int(((av == 1) & (bv == 1)).sum())
        idx = [np.where(st == s)[0] for s in np.unique(st)]
        perm = np.empty(N_PERM)
        for i in range(N_PERM):
            bp = bv.copy()
            for ix in idx:
                bp[ix] = rng.permutation(bv[ix])
            perm[i] = ((av == 1) & (bp == 1)).sum()
        p = (np.sum(perm >= obs) + 1) / (N_PERM + 1)

        gv = u[["A", col]].values
        ors = []
        for _ in range(N_BOOT):
            s = gv[rng.integers(0, len(gv), len(gv))]
            a = ((s[:, 0] == 1) & (s[:, 1] == 1)).sum()
            b = ((s[:, 0] == 1) & (s[:, 1] == 0)).sum()
            c = ((s[:, 0] == 0) & (s[:, 1] == 1)).sum()
            d = ((s[:, 0] == 0) & (s[:, 1] == 0)).sum()
            if b and c:
                ors.append((a * d) / (b * c))
        lo, hi = np.percentile(ors, [2.5, 97.5])
        a = int(((u.A == 1) & (u[col] == 1)).sum())
        b = int(((u.A == 1) & (u[col] == 0)).sum())
        c = int(((u.A == 0) & (u[col] == 1)).sum())
        d = int(((u.A == 0) & (u[col] == 0)).sum())
        print(f"\n  A x {name}: {a}/{b}/{c}/{d} (both/A only/other only/neither)")
        print(f"    observed both {100 * a / len(u):.1f}%   "
              f"independence predicts {100 * u.A.mean() * u[col].mean():.1f}%")
        print(f"    odds ratio {(a * d) / (b * c):.2f} [{lo:.2f}, {hi:.2f}]   "
              f"within-stratum permutation p = {p:.4f}")
    return u


def ordering(hot, bmv, u):
    print("\n--- 3. where do standing-threat blunders sit vs the drop? ---")
    both = u[(u.A == 1) & (u.B == 1)]
    hp = hot.set_index("gid").ply.to_dict()
    sub = bmv[bmv.gid.isin(set(both.gid))]
    rel = [("at" if r.ply == hp[r.gid] else ("before" if r.ply < hp[r.gid] else "after"))
           for r in sub.itertuples()]
    vc = pd.Series(rel).value_counts().to_dict()
    print(f"  {len(both)} games contain both, {len(rel)} standing-threat blunders in them")
    print(f"  {vc}")
    print("  'before' is 0 BY CONSTRUCTION — a standing-threat blunder is a >=200cp")
    print("  drop and the first drop is the first such drop. Do not read it as a")
    print("  finding. The informative part is that most land AFTER the drop, i.e.")
    print("  in games already decided.")


def budget(g, lev, hot, bmv, pmv, u):
    print("\n--- 4. loss budget ---")
    for label, frame in [("within the level-entry universe", u.copy()),
                         ("corpus-wide", None)]:
        if frame is None:
            frame = g[["gid", "score"]].copy()
            frame["A"] = frame.gid.isin(set(hot.gid)).astype(int)
            frame["B"] = frame.gid.isin(set(bmv.gid)).astype(int)
            frame["P"] = frame.gid.isin(set(pmv.gid)).astype(int)
        frame["loss"] = (frame.score == 0).astype(int)
        tot = int(frame.loss.sum())
        print(f"\n  {label}: {len(frame):,} games, {tot:,} losses")
        rows = [("A only", (frame.A == 1) & (frame.B == 0)),
                ("B only", (frame.A == 0) & (frame.B == 1)),
                ("both", (frame.A == 1) & (frame.B == 1)),
                ("A or B", (frame.A == 1) | (frame.B == 1)),
                ("A or B or P", (frame.A == 1) | (frame.B == 1) | (frame.P == 1)),
                ("neither A nor B", (frame.A == 0) & (frame.B == 0))]
        for lab, mk in rows:
            s = frame[mk]
            print(f"    {lab:16s} games {len(s):5,}  losses {int(s.loss.sum()):5,} "
                  f"= {100 * s.loss.sum() / tot:5.1f}%  score {100 * s.score.mean():.1f}%")

    print("\n  marginal effect of B, split on A (level-entry universe):")
    for a in (0, 1):
        s = u[u.A == a]
        wb, nb = s[s.B == 1], s[s.B == 0]
        print(f"    A={a}: with B {100 * wb.score.mean():.1f}% (n={len(wb)})  "
              f"without B {100 * nb.score.mean():.1f}% (n={len(nb)})  "
              f"delta {100 * (wb.score.mean() - nb.score.mean()):+.1f} pp")
    print("  If these were one event, B would add nothing once A has happened.")
    print("  It adds less, not nothing — consistent with a floor effect in games")
    print("  already lost, not with the two being the same failure.")


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
    m, g, fd, lg = load(d)
    lev, hot, base, bmv, pmv = events(m, fd, lg)
    gate(m, lev, hot, base, bmv)
    same_move(hot, bmv, pmv)
    u = same_game(g, lev, hot, base, bmv, pmv)
    ordering(hot, bmv, u)
    budget(g, lev, hot, bmv, pmv, u)


if __name__ == "__main__":
    main()
