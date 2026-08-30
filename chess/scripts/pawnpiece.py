#!/usr/bin/env python3
"""Do own pawn moves blunder more than own piece moves?

Pre-specified in pawnpiece_prespec.md.  Read that first.

Hypothesis from group R note theme 2: a pawn move is committal and changes the
pawn skeleton, so the position after it is least like the position that was
scanned.  Prediction: pawn moves blunder more, after controlling for
difficulty.

NOTE: features.py does NOT carry own-move SAN -- it carries `opp_prev_san`,
the opponent's previous move.  An earlier README revision said otherwise and
was wrong.  This script re-walks the annotated PGNs to recover own SAN and
merges on (gid, ply).

    python3 pawnpiece.py /home/claude/features7 <block=path.pgn> ...
"""
import os
import sys
import collections

import numpy as np
import pandas as pd
import chess
import chess.pgn

SEED = 23
NPERM = 10000
NBOOT = 2000

EXPECT_GAMES = 5404
EXPECT_ROWS = 178684
EXPECT_SCOPE = 108151
EXPECT_OPPKIND = {"check": 7.95, "capture": 8.46,
                  "pawn_break": 10.44, "quiet": 10.16}


def die(msg):
    sys.exit("GATE FAIL: %s" % msg)


def own_sans(path, user):
    """(gid, ply) -> SAN, for the player's own moves only."""
    out = {}
    n_read = n_matched = 0
    with open(path, errors="replace") as fh:
        while True:
            g = chess.pgn.read_game(fh)
            if g is None:
                break
            n_read += 1
            h = g.headers
            if h.get("White") == user:
                me = chess.WHITE
            elif h.get("Black") == user:
                me = chess.BLACK
            else:
                continue
            n_matched += 1
            gid = h.get("GameId", "") or h.get("Site", "").rsplit("/", 1)[-1]
            b, ply, node = g.board(), 0, g
            while node.variations:
                node = node.variations[0]
                ply += 1
                if b.turn == me:
                    out[(gid, ply)] = b.san(node.move)
                b.push(node.move)
    if n_read and not n_matched:
        die("%d games read from %s, none match user %r" % (n_read, path, user))
    return out


def classify(san):
    if san.startswith("O-O"):
        return "castle"
    return "piece" if san[0] in "NBRQK" else "pawn"


def strata(d):
    band = pd.cut(d.fullmove, [12, 18, 25, 35, 10 ** 9],
                  labels=["13-18", "19-25", "26-35", "36+"])
    legalq = pd.qcut(d.n_legal, 4, labels=False, duplicates="drop")
    evalb = pd.cut(d.cp_before, [-10 ** 9, -150, -50, 50, 150, 10 ** 9],
                   labels=False)
    return (band.astype(str) + "|" + legalq.astype(str) + "|"
            + evalb.astype(str) + "|" + d.in_check.astype(int).astype(str)
            + "|" + d.tc.astype(str) + "|" + d.own_cap.astype(int).astype(str))


def standardized(d):
    """Direct standardization: weight each stratum by its total row count."""
    g = d.groupby(["stratum", "kind"])["blunder"].agg(["sum", "count"])
    g = g.unstack("kind")
    ok = [s for s in g.index
          if not pd.isna(g[("count", "pawn")].get(s))
          and not pd.isna(g[("count", "piece")].get(s))]
    if not ok:
        return None, None, 0
    w = np.array([g[("count", "pawn")][s] + g[("count", "piece")][s]
                  for s in ok], float)
    rp = np.array([g[("sum", "pawn")][s] / g[("count", "pawn")][s]
                   for s in ok])
    ri = np.array([g[("sum", "piece")][s] / g[("count", "piece")][s]
                   for s in ok])
    w = w / w.sum()
    return 100 * (rp * w).sum(), 100 * (ri * w).sum(), int(
        sum(g[("count", "pawn")][s] + g[("count", "piece")][s] for s in ok))


def run_contrast(d, title, rng):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    raw_p = 100 * d[d.kind == "pawn"].blunder.mean()
    raw_i = 100 * d[d.kind == "piece"].blunder.mean()
    print("  raw            pawn %.2f%% (n=%d)   piece %.2f%% (n=%d)   "
          "diff %+.2f pp"
          % (raw_p, (d.kind == "pawn").sum(), raw_i,
             (d.kind == "piece").sum(), raw_p - raw_i))
    sp, si, used = standardized(d)
    if sp is None:
        print("  no usable strata")
        return None
    print("  standardized   pawn %.2f%%              piece %.2f%%"
          "              diff %+.2f pp" % (sp, si, sp - si))
    print("  strata retained %d of %d rows (%.1f%%), %d strata"
          % (used, len(d), 100 * used / len(d), d.stratum.nunique()))

    obs = sp - si
    kinds = d.kind.to_numpy().copy()
    pos = {s: np.where(d.stratum.to_numpy() == s)[0]
           for s in d.stratum.unique()}
    hits = 0
    for _ in range(NPERM):
        sh = kinds.copy()
        for s, p in pos.items():
            sh[p] = rng.permutation(sh[p])
        d2 = d.assign(kind=sh)
        a, b, _ = standardized(d2)
        if a is not None and abs(a - b) >= abs(obs):
            hits += 1
    p = (hits + 1) / (NPERM + 1)
    print("  permutation within stratum, %d draws, seed %d:  p = %.4f"
          % (NPERM, SEED, p))
    return obs, p


def main():
    feat = sys.argv[1]
    blocks = [s.split("=", 1) for s in sys.argv[2:]]

    print("=" * 78)
    print("PAWN vs PIECE MOVES — pre-specified in pawnpiece_prespec.md")
    print("=" * 78)

    games = pd.read_csv(os.path.join(feat, "games.csv"),
                        dtype={"block": str, "gid": str})
    mv = pd.read_csv(os.path.join(feat, "moves.csv.gz"),
                     dtype={"block": str, "gid": str})
    print("\n[gate 1] features run identity")
    print("  games %d (expect %d), rows %d (expect %d)"
          % (len(games), EXPECT_GAMES, len(mv), EXPECT_ROWS))
    if len(games) != EXPECT_GAMES or len(mv) != EXPECT_ROWS:
        die("this is not the seven-block 5,404-game run")

    d = mv[(mv.fullmove > 12) & (mv.mate_flag == 0)].copy()
    print("\n[gate 2] in-scope rows %d (expect %d)" % (len(d), EXPECT_SCOPE))
    if len(d) != EXPECT_SCOPE:
        die("scope is %d rows, oppmove.py published %d"
            % (len(d), EXPECT_SCOPE))

    d["blunder"] = (d.drop_cp >= 200).astype(float)
    print("\n[gate 3] oppmove.py raw crosstab (independent of this analysis)")
    bad = []
    for k, want in EXPECT_OPPKIND.items():
        got = 100 * d[d.opp_prev_kind == k].blunder.mean()
        ok = abs(got - want) <= 0.02
        print("  %-11s %6.2f%% (expect %.2f)  %s"
              % (k, got, want, "ok" if ok else "MISMATCH"))
        if not ok:
            bad.append(k)
    if bad:
        die("oppmove crosstab does not reproduce: %s" % ", ".join(bad))

    print("\n[gate 4] recovering own-move SAN from the PGNs")
    san = {}
    for name, path in blocks:
        user = "justinmorg" if name.startswith("CC") else "jamorgan"
        s = own_sans(path, user)
        san.update(s)
        print("  %-12s %7d own moves  (user %s)" % (name, len(s), user))
    key = list(zip(d.gid, d.ply))
    d["san"] = [san.get(k) for k in key]
    cov = d.san.notna().mean()
    print("  merge coverage %.2f%% of in-scope rows" % (100 * cov))
    if cov < 0.995:
        die("SAN merge covers only %.2f%% of rows" % (100 * cov))
    print("\nall gates passed")

    d = d[d.san.notna()].copy()
    d["kind"] = [classify(s) for s in d.san]
    d["own_cap"] = ["x" in s for s in d.san]

    n_castle = (d.kind == "castle").sum()
    print("\n  castling excluded as pre-specified: %d rows (%.2f%%), "
          "blunder rate %.2f%%"
          % (n_castle, 100 * n_castle / len(d),
             100 * d[d.kind == "castle"].blunder.mean()))
    d = d[d.kind != "castle"].copy()
    d["stratum"] = strata(d)

    rng = np.random.default_rng(SEED)
    primary = run_contrast(d, "PRIMARY (decision rule: p < 0.01, pawn worse)",
                           rng)

    hot = d[(d.fullmove >= 13) & (d.fullmove <= 25)
            & (d.npm_light >= 13)].copy()
    secondary = run_contrast(
        hot, "SECONDARY — hot zone only (EXPLORATORY, not the rule)", rng)

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    obs, p = primary
    if p < 0.01 and obs > 0:
        print("  %+.2f pp at p = %.4f, pawn worse -> POSITIVE per the rule."
              % (obs, p))
    elif p < 0.01 and obs < 0:
        print("  %+.2f pp at p = %.4f -- significant but in the OPPOSITE"
              % (obs, p))
        print("  direction from the prediction. The hypothesis as stated is"
              " refuted,")
        print("  not confirmed. Report as a reversal.")
    else:
        print("  %+.2f pp at p = %.4f, does not clear 0.01 -> NULL per the rule."
              % (obs, p))
    if secondary:
        o2, p2 = secondary
        print("  hot zone (exploratory): %+.2f pp at p = %.4f%s"
              % (o2, p2, "  -> FLAG only" if p2 < 0.01 else ""))


if __name__ == "__main__":
    main()
