#!/usr/bin/env python3
"""Thread 2: the first major deterioration, per game.

Reads the features.py tables and answers, for games entered level in the
middlegame: when does the first big eval drop happen, does it stick, and what
kind of move is it?  No PGN walk and no engine — everything is a groupby on
moves.csv.gz, which is the point of that table.

Usage:
    python3 firstdrop.py [features_dir]       # default /home/claude/features

Writes features_dir/firstdrop/firstdrop_{100,200,300}.csv (one row per game
with a drop, recovery flags at N=3/5/8) and level_games.csv (per-game
middlegame-entry eval and bucket).  Outputs are derived tables, same policy as
the features tables themselves: not committed, regenerate on demand.

Definitions, chosen deliberately (the README records the sensitivity):
  * first drop  — first own move with drop_cp >= T (T in 100/200/300),
                  mate_flag == 0.
  * recovered   — within the next N own moves (N in 3/5/8), cp_after gets back
                  to within 50cp of cp_before at the drop.  Permanent = not.
  * mg entry    — the first position of fullmove 13 with npm_light > 14,
                  measured SIDE-AWARE:
                    white: cp_before of own move 13
                    black: cp_after  of own move 12
                  Measuring cp_before of the first own move >= 13 for both
                  colours reads the position AFTER the opponent's move for
                  Black, and opponent errors systematically inflate that eval
                  — it shifted ~280 games from level into up when tried.
                  This own-move proxy recovers the phase map's every-ply
                  buckets to within 0.5-2% (4,600 games vs 4,637; the 37-game
                  gap is games with no own move at the entry ply).

Validation gates, on the features.py precedent — hard exit rather than a
plausible wrong table:
  1. 5,404 games / 178,684 own-move rows in the input.
  2. games.csv bucket counts reproduce (2865/804/529/466/740).
  3. mg-entry buckets reproduce (4,600 = 1,662 up / 1,930 level / 1,008 down).
"""
import os
import sys

import numpy as np
import pandas as pd

FEAT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
OUT = os.path.join(FEAT, "firstdrop")

THRESHOLDS = (100, 200, 300)
RECOV_NS = (3, 5, 8)
RECOV_MARGIN = 50

NPM_BANDS = ["24-20", "19-13", "12-8", "7-0"]
FM_BANDS = ["1-12", "13-18", "19-25", "26+"]


def npm_band(x):
    return "24-20" if x >= 20 else "19-13" if x >= 13 else "12-8" if x >= 8 else "7-0"


def fm_band(x):
    return "1-12" if x <= 12 else "13-18" if x <= 18 else "19-25" if x <= 25 else "26+"


def main():
    m = pd.read_csv(os.path.join(FEAT, "moves.csv.gz"), low_memory=False)
    g = pd.read_csv(os.path.join(FEAT, "games.csv"))

    # ---- gate 1: corpus size -------------------------------------------------
    if len(g) != 5404 or len(m) != 178684:
        sys.exit(f"ERROR: expected 5,404 games / 178,684 rows, got "
                 f"{len(g)} / {len(m)}. Wrong features run — see README setup.")

    # ---- gate 2: published bucket counts ------------------------------------
    want = {"reached": 2865, "no_eligible": 804, "even": 529,
            "losing": 466, "lost": 740}
    got = g.bucket.value_counts().to_dict()
    if got != want:
        sys.exit(f"ERROR: games.csv buckets {got} != published {want}")

    m = m.sort_values(["gid", "ply"]).reset_index(drop=True)
    m["own_idx"] = m.groupby("gid").cumcount()
    m["color"] = m.gid.map(g.set_index("gid").color)

    # ---- middlegame entry, side-aware ---------------------------------------
    w = (m[(m.color == "white") & (m.fullmove >= 13) & (m.npm_light > 14)]
         .groupby("gid").first()["cp_before"])
    b_last = m[(m.color == "black") & (m.fullmove <= 12)].groupby("gid").last()
    b = b_last[b_last.fullmove == 12]["cp_after"]
    entry = pd.concat([w, b]).rename("mg_entry_cp")
    reached13 = set(m[(m.fullmove >= 13) & (m.npm_light > 14)].gid)
    lev = g.merge(entry, on="gid", how="left")
    lev["has_mg"] = lev.gid.isin(reached13)
    hm = lev[lev.has_mg & lev.mg_entry_cp.notna()]
    n_up = int((hm.mg_entry_cp > 100).sum())
    n_level = int(((hm.mg_entry_cp > -100) & (hm.mg_entry_cp <= 100)).sum())
    n_down = int((hm.mg_entry_cp <= -100).sum())

    # ---- gate 3: mg-entry buckets -------------------------------------------
    if (len(hm), n_up, n_level, n_down) != (4600, 1662, 1930, 1008):
        sys.exit(f"ERROR: mg-entry buckets ({len(hm)}, {n_up}, {n_level}, "
                 f"{n_down}) != published (4600, 1662, 1930, 1008)")
    print(f"gates OK: 5,404 games / 178,684 rows; buckets reproduce; "
          f"mg entry {len(hm)} = {n_up} up / {n_level} level / {n_down} down")

    os.makedirs(OUT, exist_ok=True)
    lev["entry_bucket"] = np.select(
        [~lev.has_mg | lev.mg_entry_cp.isna(),
         lev.mg_entry_cp > 100, lev.mg_entry_cp <= -100],
        ["no_mg", "up", "down"], default="level")
    lev[["gid", "block", "score", "mg_entry_cp", "has_mg", "entry_bucket"]] \
        .to_csv(os.path.join(OUT, "level_games.csv"), index=False)

    level_gids = set(lev[lev.entry_bucket == "level"].gid)

    # cp_after series per game for the recovery check
    cp_after = m.pivot_table(index="gid", columns="own_idx", values="cp_after")

    keep = ["gid", "block", "own_idx", "ply", "fullmove", "npm_light",
            "cp_before", "cp_after", "drop_cp", "wp_error", "spend", "clk",
            "hang_label", "see_standing", "opp_created_threat",
            "opp_prev_kind", "opp_prev_san", "in_check"]

    firsts = {}
    for thr in THRESHOLDS:
        hit = m[(m.drop_cp >= thr) & (m.mate_flag == 0)]
        first = hit.groupby("gid").first().reset_index()[keep].copy()
        for N in RECOV_NS:
            rec = []
            for gid, oi, cpb in zip(first.gid, first.own_idx, first.cp_before):
                row = cp_after.loc[gid]
                w_ = row.iloc[int(oi) + 1: int(oi) + 1 + N].dropna()
                rec.append(bool(len(w_) and w_.max() >= cpb - RECOV_MARGIN))
            first[f"rec{N}"] = rec
        first.to_csv(os.path.join(OUT, f"firstdrop_{thr}.csv"), index=False)
        firsts[thr] = first
        print(f"thr {thr}: {len(first)} games with a drop "
              f"({len(first) / len(g) * 100:.0f}%)")

    # ================= the README tables, level games, thr 200 / N 5 =========
    first = firsts[200]
    fl = first[first.gid.isin(level_gids)]
    lg = lev[lev.entry_bucket == "level"].merge(
        fl[["gid", "fullmove", "npm_light", "rec5"]], on="gid", how="left")

    print("\n--- level-at-entry games, by first-drop fate (thr 200, N=5) ---")
    for name, s in [("no 200cp drop ever", lg[lg.rec5.isna()]),
                    ("recovered <=5 own moves", lg[lg.rec5 == True]),   # noqa: E712
                    ("permanent", lg[lg.rec5 == False])]:               # noqa: E712
        print(f"  {name:26} n={len(s):5}  score {s.score.mean() * 100:5.1f}%")
    print("  (gradient partly definitional — losing games contain drops; "
          "the findings are the timing, permanence and mechanism)")

    print(f"\n  first-drop timing: median fullmove {fl.fullmove.median():.0f}, "
          f"IQR {fl.fullmove.quantile(.25):.0f}-{fl.fullmove.quantile(.75):.0f}")
    pfd = fl[fl.rec5 == False]                                          # noqa: E712
    hz = (pfd.fullmove.between(13, 25)) & (pfd.npm_light >= 13)
    print(f"  permanent drops in moves 13-25 at npm>=13 (hot zone): "
          f"{hz.mean() * 100:.0f}%")

    # ---- hazard cross-tab ----------------------------------------------------
    drop_at = fl.set_index("gid")["own_idx"]
    mm = m[m.gid.isin(level_gids)].copy()
    mm["cut"] = mm.gid.map(drop_at)
    ar = mm[((mm.cut.isna()) | (mm.own_idx <= mm.cut)) & (mm.mate_flag == 0)].copy()
    ar["nb"] = ar.npm_light.apply(npm_band)
    ar["fb"] = ar.fullmove.apply(fm_band)
    fl2 = fl.copy()
    fl2["nb"] = fl2.npm_light.apply(npm_band)
    fl2["fb"] = fl2.fullmove.apply(fm_band)
    risk = ar.pivot_table(index="nb", columns="fb", values="gid",
                          aggfunc="count").reindex(NPM_BANDS)[FM_BANDS]
    drops = fl2.pivot_table(index="nb", columns="fb", values="gid",
                            aggfunc="count").reindex(NPM_BANDS)[FM_BANDS]
    print("\n--- first-drop hazard per 100 at-risk own moves "
          "(npm band x move band), level games ---")
    print((drops / risk * 100).round(2).fillna("-").to_string())
    print("\nat-risk own moves:")
    print(risk.fillna(0).astype(int).to_string())

    # ---- mechanism at permanent hot-zone drops ------------------------------
    hot = pfd[(pfd.fullmove.between(13, 25)) & (pfd.npm_light >= 13)]
    base = m[(m.gid.isin(level_gids)) & (m.fullmove.between(13, 25))
             & (m.npm_light >= 13) & (m.mate_flag == 0)]
    print(f"\n--- mechanism, permanent hot-zone first drops (n={len(hot)}) ---")
    print(f"  hang_label: {hot.hang_label.value_counts(dropna=False).to_dict()}")
    print(f"  see_standing>=150: {(hot.see_standing >= 150).mean() * 100:.0f}% "
          f"(baseline {(base.see_standing >= 150).mean() * 100:.0f}%)")
    print(f"  opp_created_threat: {hot.opp_created_threat.mean() * 100:.0f}% "
          f"(baseline {base.opp_created_threat.mean() * 100:.0f}%)")
    print(f"  opp prev kind: "
          f"{hot.opp_prev_kind.value_counts(normalize=True).round(3).to_dict()}")
    print(f"  spend: median {hot.spend.median():.1f}s "
          f"(baseline {base.spend.median():.1f}s); "
          f"<=2s {(hot.spend <= 2).mean() * 100:.0f}%, "
          f">=8s {(hot.spend >= 8).mean() * 100:.0f}%")
    print(f"  in check: {hot.in_check.mean() * 100:.0f}%")

    # ---- block stability -----------------------------------------------------
    print("\n--- by block: n_level | permanent share | "
          "score (no drop / recovered / permanent) ---")
    for blk, s in lg.groupby("block"):
        nd, rc, pm = (s[s.rec5.isna()], s[s.rec5 == True],                # noqa: E712
                      s[s.rec5 == False])                                 # noqa: E712
        print(f"  {blk:10} {len(s):4} | {len(pm) / len(s) * 100:4.0f}% | "
              f"{nd.score.mean() * 100:4.0f} / {rc.score.mean() * 100:4.0f} / "
              f"{pm.score.mean() * 100:4.0f}")

    # ---- sensitivity ---------------------------------------------------------
    print("\n--- sensitivity: threshold x recovery window ---")
    for thr in (200, 300):
        f_ = firsts[thr][firsts[thr].gid.isin(level_gids)]
        for N in RECOV_NS:
            perm = f_[f_[f"rec{N}"] == False]                             # noqa: E712
            lgx = lev[lev.entry_bucket == "level"].merge(
                perm[["gid", "fullmove"]], on="gid", how="left")
            share = lgx.fullmove.notna().mean() * 100
            sc = lgx[lgx.fullmove.notna()].score.mean() * 100
            hzs = ((perm.fullmove.between(13, 25))
                   & (perm.npm_light >= 13)).mean() * 100
            print(f"  thr {thr} N {N}: permanent share {share:.0f}%  "
                  f"score {sc:.1f}%  median fm {perm.fullmove.median():.0f}  "
                  f"hot-zone share {hzs:.0f}%")

    print(f"\nwrote {OUT}/firstdrop_{{100,200,300}}.csv and level_games.csv")


if __name__ == "__main__":
    main()
