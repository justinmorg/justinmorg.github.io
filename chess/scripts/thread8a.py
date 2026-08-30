#!/usr/bin/env python3
"""Thread 8 channel A: does leaving book early produce a worse position?

Pre-specified in thread8a_prespec.md.  Read that first; the decision rule was
written before any output here was inspected.

Held-out by design: the book node table is built on 2025-09-01 -> 2026-04-30
and only games from 2026-05-01 -> 2026-08-19 are scored.  Book status is
defined partly by move times, so training and scoring on the same games would
be circular in exactly the direction the hypothesis predicts.

Validation-gated on the features.py / firstdrop.py precedent: it hard-exits
unless openings.py's clock gate passes, the published openings figures
reproduce, and the features run is the 5,636-game eight-block one.

    python3 thread8a.py /home/claude/features
"""
import os
import sys
import statistics as st
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chess
import openings as OP

SEED = 23
NPERM = 10000
MIN_FAM = 30
TRAIN = ("2025-09-01", "2026-04-30")
TEST = ("2026-05-01", "2026-08-19")
TC = {"180+2", "300+0"}

# published figures this run must reproduce before anything is believed
EXPECT_FULL_GAMES = 1772
EXPECT_INBOOK = 1.38
EXPECT_OUTBOOK = 2.53
EXPECT_D4 = (881, 882)
EXPECT_FEAT_GAMES = 5636
EXPECT_EV12_N = 1643
EXPECT_EV12_SD = 265


def die(msg):
    sys.exit("GATE FAIL: %s" % msg)


def load(paths, since, until):
    out = []
    for p in paths:
        out.extend(OP.parse(p, "jamorgan", TC, since, until, 40))
    return out


def build_tree(games):
    t = OP.Tree()
    for g in games:
        t.add(g)
    return t


def depth_of(g, tree, min_reps=25):
    """Book depth using report_depth's definition, unchanged.

    One addition report_depth does not need: a test-window game can reach a
    position the train-window tree never saw.  `Tree.nd` is a defaultdict, so
    calling summary() on a missing key both crashes and silently inserts an
    empty node.  An unseen position is by definition not a book node, so the
    depth simply stops there.
    """
    b = chess.Board()
    mycol = chess.WHITE if g["col"] == 0 else chess.BLACK
    depth = 0
    for i, (san, sp) in enumerate(g["seq"]):
        if b.turn == mycol:
            k = (g["col"], b.epd())
            if k not in tree.nd:
                break
            s = tree.summary(k)
            if OP.is_book(s, min_reps) and s["san"] == san:
                depth += 1
            else:
                break
        b.push(b.parse_san(san))
    return depth


def family_of(g):
    if g["col"] == 0:
        return "White 1.d4 " + (g["seq"][1][0] if len(g["seq"]) > 1 else "?")
    return "Black vs 1." + g["seq"][0][0]


def book_times(games, tree):
    """Reproduce the published in-book / first-out-of-book means."""
    intime, outtime = [], []
    for g in games:
        b = chess.Board()
        mycol = chess.WHITE if g["col"] == 0 else chess.BLACK
        done = False
        for i, (san, sp) in enumerate(g["seq"]):
            if b.turn == mycol and not done:
                s = tree.summary((g["col"], b.epd()))
                if OP.is_book(s, 25) and s["san"] == san:
                    if sp is not None and i > 1:
                        intime.append(sp)
                else:
                    done = True
                    if sp is not None and i > 1:
                        outtime.append(sp)
            b.push(b.parse_san(san))
    return (sum(intime) / len(intime), sum(outtime) / len(outtime))


def spearman(x, y):
    if len(x) < 3:
        return 0.0
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def pooled_rho(df, ycol):
    """Sample-size-weighted mean of within-family Spearman correlations."""
    num = den = 0.0
    for f, d in df.groupby("family"):
        d = d.dropna(subset=[ycol])
        if len(d) < 3:
            continue
        num += len(d) * spearman(d["depth"].to_numpy(), d[ycol].to_numpy())
        den += len(d)
    return num / den if den else 0.0


def perm_p(df, ycol, rng):
    obs = pooled_rho(df, ycol)
    d = df.dropna(subset=[ycol]).copy()
    hits = 0
    idx = {f: g.index.to_numpy() for f, g in d.groupby("family")}
    depth = d["depth"].to_numpy().copy()
    pos = {f: d.index.get_indexer(v) for f, v in idx.items()}
    for _ in range(NPERM):
        sh = depth.copy()
        for f, p in pos.items():
            sh[p] = rng.permutation(sh[p])
        d2 = d.assign(depth=sh)
        if abs(pooled_rho(d2, ycol)) >= abs(obs):
            hits += 1
    return obs, (hits + 1) / (NPERM + 1)


def mde(n1, n2, sd, alpha=0.01, power=0.80):
    """Two-sided MDE in the units of sd."""
    from math import sqrt
    za, zb = 2.5758, 0.8416          # alpha=0.01 two-sided, power=0.80
    return (za + zb) * sd * sqrt(1.0 / n1 + 1.0 / n2)


def main():
    feat = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

    print("=" * 78)
    print("THREAD 8 CHANNEL A — pre-specified in thread8a_prespec.md")
    print("=" * 78)

    # ---- gate 1: clock arithmetic
    print("\n[gate 1] openings.py clock gate")
    OP.gate(data)

    # ---- gate 2: published openings figures, full window
    paths = [os.path.join(data, f) for f in (
        "jamorgan_blitz_2025q3_analyzed.pgn.gz",
        "jamorgan_blitz_2025q4_analyzed.pgn.gz",
        "jamorgan_blitz_2026_analyzed.pgn.gz")]
    full = load(paths, "2025-08-31", "2026-08-19")
    print("\n[gate 2] full-window rebuild")
    print("  games %d (expect %d)" % (len(full), EXPECT_FULL_GAMES))
    if len(full) != EXPECT_FULL_GAMES:
        die("full window is %d games, published is %d"
            % (len(full), EXPECT_FULL_GAMES))
    ft = build_tree(full)
    ib, ob = book_times(full, ft)
    print("  in-book %.2fs (expect %.2f) / out-of-book %.2fs (expect %.2f)"
          % (ib, EXPECT_INBOOK, ob, EXPECT_OUTBOOK))
    if abs(ib - EXPECT_INBOOK) > 0.03 or abs(ob - EXPECT_OUTBOOK) > 0.03:
        die("book time gap does not reproduce")
    w = [g for g in full if g["col"] == 0]
    d4 = sum(1 for g in w if g["seq"][0][0] == "d4")
    print("  1.d4 as White %d/%d (expect %d/%d)"
          % (d4, len(w), *EXPECT_D4))
    if (d4, len(w)) != EXPECT_D4:
        die("first-move adherence does not reproduce")

    # ---- gate 3+4: features run identity and eval@12 distribution
    print("\n[gate 3] features.py run identity")
    games = pd.read_csv(os.path.join(feat, "games.csv"),
                        dtype={"block": str, "gid": str})
    print("  games.csv rows %d (expect %d)" % (len(games), EXPECT_FEAT_GAMES))
    if len(games) != EXPECT_FEAT_GAMES:
        die("features run is %d games, expected the %d-game eight-block run"
            % (len(games), EXPECT_FEAT_GAMES))

    mv = pd.read_csv(os.path.join(feat, "moves.csv.gz"),
                     dtype={"block": str, "gid": str})
    e12 = mv[(mv.fullmove == 12) & (mv.mate_flag == 0)]
    e12 = e12.drop_duplicates("gid").set_index("gid")["cp_after"]

    fullids = {g["gid"] for g in full}
    chk = e12[e12.index.isin(fullids)]
    print("\n[gate 4] eval@12 over the full window")
    print("  n %d (expect ~%d), sd %.0f (expect ~%d)"
          % (len(chk), EXPECT_EV12_N, chk.std(), EXPECT_EV12_SD))
    if abs(len(chk) - EXPECT_EV12_N) > 25 or abs(chk.std() - EXPECT_EV12_SD) > 15:
        die("eval@12 distribution does not reproduce the published figures")
    print("\nall gates passed\n")

    # ---- build held-out node table and score the test window
    train = [g for g in full if TRAIN[0] <= g["date"] <= TRAIN[1]]
    test = [g for g in full if TEST[0] <= g["date"] <= TEST[1]]
    print("=" * 78)
    print("HELD-OUT DESIGN")
    print("=" * 78)
    print("  train %s..%s : %d games (node table only)" % (*TRAIN, len(train)))
    print("  test  %s..%s : %d games (scored)" % (*TEST, len(test)))
    tree = build_tree(train)

    gi = games.set_index("gid")
    rows = []
    for g in test:
        gid = g["gid"]
        if gid not in gi.index:
            continue
        r = gi.loc[gid]
        rows.append(dict(gid=gid, family=family_of(g),
                         depth=depth_of(g, tree),
                         opp_elo=r["opp_elo"], tc=r["tc"],
                         o1=e12.get(gid, np.nan),
                         o3=1.0 if r["peak"] >= 200 else 0.0))
    df = pd.DataFrame(rows)
    df["o2"] = np.where(df.o1.isna(), np.nan, (df.o1 <= -100).astype(float))

    print("\n  scored games matched to features: %d" % len(df))
    print("  with usable eval@12            : %d" % df.o1.notna().sum())

    print("\n  book depth distribution (test window):")
    for d, n in sorted(df.depth.value_counts().items()):
        print("    depth %d : %4d  (%.1f%%)" % (d, n, 100 * n / len(df)))

    print("\n  families:")
    keep = []
    for f, d in sorted(df.groupby("family"), key=lambda kv: -len(kv[1])):
        mark = "included" if len(d) >= MIN_FAM else "DROPPED (<%d)" % MIN_FAM
        print("    %-26s n=%4d  median depth %.1f   %s"
              % (f, len(d), d.depth.median(), mark))
        if len(d) >= MIN_FAM:
            keep.append(f)
    sub = df[df.family.isin(keep)].copy()
    print("\n  included: %d families, %d games" % (len(keep), len(sub)))

    # ---- covariate check
    rho_elo = pooled_rho(sub.rename(columns={"opp_elo": "_y"}), "_y")
    print("\n  covariate check: pooled rho(depth, opp_elo) = %+.3f%s"
          % (rho_elo, "  -> ROBUSTNESS RUN REQUIRED" if abs(rho_elo) > 0.10
             else "  (below 0.10, no robustness run needed)"))

    # ---- the test
    rng = np.random.default_rng(SEED)
    print("\n" + "=" * 78)
    print("PRE-SPECIFIED TEST  (positive finding requires p < 0.01 on O1)")
    print("=" * 78)
    print("  %-38s %8s %10s %8s" % ("outcome", "n", "rho", "p"))
    res = {}
    for col, name in (("o1", "O1 eval@12 (cp, primary)"),
                      ("o2", "O2 share <= -100cp"),
                      ("o3", "O3 reached >= +200")):
        obs, p = perm_p(sub, col, rng)
        res[col] = (obs, p)
        print("  %-38s %8d %+10.3f %8.4f"
              % (name, sub[col].notna().sum(), obs, p))

    # ---- descriptive split + resolution
    print("\n" + "=" * 78)
    print("DESCRIPTIVE (not the test): within-family median split")
    print("=" * 78)
    sub["arm"] = ""
    for f, d in sub.groupby("family"):
        med = d.depth.median()
        sub.loc[d.index, "arm"] = np.where(d.depth < med, "shallow", "deep")
    print("  %-26s %6s %6s %10s %10s"
          % ("family", "shal", "deep", "O1 shal", "O1 deep"))
    for f, d in sorted(sub.groupby("family"), key=lambda kv: -len(kv[1])):
        s = d[d.arm == "shallow"].o1.dropna()
        p_ = d[d.arm == "deep"].o1.dropna()
        print("  %-26s %6d %6d %10s %10s"
              % (f, len(s), len(p_),
                 "%+.0f" % s.mean() if len(s) else "-",
                 "%+.0f" % p_.mean() if len(p_) else "-"))
    s_all = sub[sub.arm == "shallow"].o1.dropna()
    d_all = sub[sub.arm == "deep"].o1.dropna()
    sd = sub.o1.dropna().std()
    print("\n  pooled: shallow n=%d mean %+.0fcp | deep n=%d mean %+.0fcp"
          % (len(s_all), s_all.mean(), len(d_all), d_all.mean()))
    print("  eval@12 sd in test window: %.0fcp" % sd)
    if len(s_all) and len(d_all):
        print("\n  RESOLUTION: this held-out test detects a difference of"
              " %.0fcp" % mde(len(s_all), len(d_all), sd))
        print("  (80%% power, alpha 0.01, two-sided, on the median-split arms)")
        print("  The README's 45cp figure is for all 1,772 full-window games")
        print("  and overstates what this held-out test can resolve.")

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    o1p = res["o1"][1]
    if o1p < 0.01:
        print("  O1 p = %.4f < 0.01 -> POSITIVE per the pre-specified rule."
              % o1p)
    else:
        print("  O1 p = %.4f, does not clear 0.01 -> NULL per the"
              " pre-specified rule." % o1p)
        flags = [n for n, c in (("O2", "o2"), ("O3", "o3")) if res[c][1] < 0.01]
        if flags:
            print("  %s clears 0.01 without O1: FLAG, not a finding"
                  " (three outcomes tested)." % ", ".join(flags))
        else:
            print("  O2 and O3 also null. No flags.")


if __name__ == "__main__":
    main()
