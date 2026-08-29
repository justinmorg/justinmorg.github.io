#!/usr/bin/env python3
"""The quiet-punishment 43% — characterizing the residual of H2.

H2: 57% of the 330 permanent hot-zone judgment drops lose to an immediate
capture or check. The other 43% is currently defined only by what it is NOT,
which is the weakest kind of category to be left holding, and no forcing-move
check will ever catch it.

This is the FREE half: everything derivable from columns already in
moves.csv.gz plus forcingtest.csv. The PAID half — playing out depth-16 PVs
6-10 plies to separate a DELAYED tactic from genuine positional decay — is
deliberately not done here. The 143 positions are written to quiet43.csv,
sorted worst-first, for whoever runs it.

Sections:
  1  how the two halves differ, all columns, permutation on the group label
  2  severity
  3  eval trajectory over the next 5 own moves (with its floor-effect caveat)
  4  block split
  5  handoff file
  6  is the opponent-Elo gap real, or the chess.com pool?
  7  proper test of the section 3 trajectory difference

Usage:
    python3 chess/scripts/forcingtest.py /home/claude/features   # prerequisite
    python3 chess/scripts/quiet43.py     /home/claude/features
"""
import os
import sys

import numpy as np
import pandas as pd

RNG = np.random.default_rng(23)

COLS = ["spend", "wp_error", "drop_cp", "cp_before", "cp_after", "fullmove",
        "npm_light", "n_legal", "n_caps_avail", "n_opp_caps", "king_attackers",
        "queens_on", "mat_bal", "block", "site"]
REPORT = ["spend", "wp_error", "drop_cp", "cp_before", "cp_after", "fullmove",
          "npm_light", "n_legal", "n_caps_avail", "n_opp_caps", "king_attackers",
          "queens_on", "mat_bal", "opp_elo", "n_plies", "score"]


def perm_p(a, b, n=10000, stat=np.mean):
    obs = stat(a) - stat(b)
    pool = np.concatenate([a, b])
    d = np.empty(n)
    for i in range(n):
        p = RNG.permutation(pool)
        d[i] = stat(p[:len(a)]) - stat(p[len(a):])
    return obs, (np.sum(np.abs(d) >= abs(obs)) + 1) / (n + 1)


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
    fp = os.path.join(d, "forcingtest.csv")
    if not os.path.exists(fp):
        sys.exit("FATAL: run forcingtest.py first (needs Stockfish)")
    ft = pd.read_csv(fp, dtype={"gid": str})
    m = pd.read_csv(os.path.join(d, "moves.csv.gz"), dtype={"block": str, "gid": str})
    g = pd.read_csv(os.path.join(d, "games.csv"), dtype={"block": str, "gid": str})

    T = ft[ft.grp == "T"].copy()
    if len(T) != 330:
        sys.exit(f"FATAL: treatment should be 330, got {len(T)}")
    rf = T.reply_forcing.mean()
    if abs(100 * rf - 57) > 1:
        sys.exit(f"FATAL: reply-forcing should be 57%, got {100*rf:.0f}%")
    print(f"gate OK: treatment n={len(T)}, reply forcing {100*rf:.0f}%")

    T = T.merge(m[["gid", "ply"] + COLS], on=["gid", "ply"], how="left")
    T = T.merge(g[["gid", "score", "opp_elo", "n_plies"]], on="gid", how="left")
    Q, F = T[T.reply_forcing == 0], T[T.reply_forcing == 1]
    print(f"quiet-punished n={len(Q)} ({100*len(Q)/len(T):.0f}%), "
          f"forcing-punished n={len(F)}")

    print("\n--- 1. how do the two halves differ? ---")
    print(f"{'metric':16s} {'quiet':>10s} {'forcing':>10s} {'diff':>10s} {'p':>8s}")
    for c in REPORT:
        a = Q[c].dropna().values.astype(float)
        b = F[c].dropna().values.astype(float)
        o, p = perm_p(a, b)
        print(f"{c:16s} {a.mean():10.3f} {b.mean():10.3f} {o:+10.3f} {p:8.4f}"
              f"{' *' if p < 0.05 else ''}")

    print("\n--- 2. severity ---")
    for name, s in [("quiet-punished", Q), ("forcing-punished", F)]:
        print(f"  {name:18s} median wp_error {s.wp_error.median():.3f}  "
              f"median drop_cp {s.drop_cp.median():.0f}  "
              f"eval after {s.cp_after.median():+.0f}cp  score {100*s.score.mean():.1f}%")

    print("\n--- 3. eval trajectory over the next 5 own moves ---")
    rows = []
    for r in T.itertuples():
        sub = m[(m.gid == r.gid) & (m.ply > r.ply)].sort_values("ply").head(5)
        if len(sub) >= 3:
            rows.append({"q": int(r.reply_forcing == 0), "atdrop": r.cp_after,
                         "p3": sub.cp_after.iloc[2], "p5": sub.cp_after.iloc[-1]})
    tr = pd.DataFrame(rows)
    for q, name in [(1, "quiet-punished"), (0, "forcing-punished")]:
        s = tr[tr.q == q]
        print(f"  {name:18s} n={len(s):3d}  median {s.atdrop.median():+.0f} -> "
              f"+3 moves {s.p3.median():+.0f} -> +5 {s.p5.median():+.0f}")

    print("\n--- 4. block split ---")
    print(T.assign(quiet=(T.reply_forcing == 0).astype(int))
          .groupby("block").agg(n=("quiet", "size"), quiet_share=("quiet", "mean"))
          .assign(quiet_share=lambda x: (100 * x.quiet_share).round(0)).to_string())

    print("\n--- 5. handoff ---")
    out = os.path.join(d, "quiet43.csv")
    Q[["gid", "ply", "fullmove", "cp_before", "cp_after", "drop_cp", "wp_error",
       "spend", "block", "site"]].sort_values("wp_error", ascending=False) \
        .to_csv(out, index=False)
    print(f"  {len(Q)} positions -> {out} (worst-first). Paid half: depth-16 PV")
    print("  playout 6-10 plies, split delayed-tactic vs positional.")

    print("\n--- 6. is the opp_elo gap real, or the chess.com pool? ---")
    L, C = T[T.site == "lichess"], T[T.site != "lichess"]
    o, p = perm_p((L.reply_forcing == 0).values.astype(float),
                  (C.reply_forcing == 0).values.astype(float))
    print(f"  quiet share: Lichess {100*(L.reply_forcing==0).mean():.0f}% (n={len(L)}) "
          f"vs chess.com {100*(C.reply_forcing==0).mean():.0f}% (n={len(C)}); "
          f"{100*o:+.1f} pp, p={p:.4f}")
    a = L[L.reply_forcing == 0].opp_elo.values.astype(float)
    b = L[L.reply_forcing == 1].opp_elo.values.astype(float)
    o, p = perm_p(a, b)
    print(f"  WITHIN Lichess, opp_elo quiet vs forcing: {a.mean():.0f} vs {b.mean():.0f}, "
          f"{o:+.0f}, p={p:.4f}  -> the corpus-wide gap is pool calibration")
    dm = T[T.block.isin(["2024H2", "CC-2024Q4"])].assign(
        q=lambda x: (x.reply_forcing == 0).astype(float))
    o, p = perm_p(dm[dm.block == "2024H2"].q.values,
                  dm[dm.block == "CC-2024Q4"].q.values)
    print(f"  date-matched Sep-Dec 2024 site contrast: {100*o:+.1f} pp, p={p:.4f}"
          f"  -> the site difference does NOT survive date matching")

    print("\n--- 7. proper test of the section 3 trajectory difference ---")
    tr["slide"] = tr.p5 - tr.atdrop
    o, p = perm_p(tr[tr.q == 1].slide.values.astype(float),
                  tr[tr.q == 0].slide.values.astype(float), stat=np.median)
    print(f"  further slide, quiet minus forcing: {o:+.0f}cp, p={p:.4f}")
    print("  NULL, and forcing-punished start lower so a floor effect is live.")
    print("  Do not quote the raw trajectory numbers as a finding.")


if __name__ == "__main__":
    main()
