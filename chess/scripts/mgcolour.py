#!/usr/bin/env python3
"""
mgcolour.py — middlegame error rate by colour and repertoire family, me vs
same-game opponents. Exploratory, not pre-specified (2026-10-24).

Usage:
    python3 mgcolour.py FEATLIC FEATOPP BLOCK.pgn [BLOCK.pgn ...]

FEATLIC / FEATOPP: features.py on the six settled Lichess blocks for Justin and
for the opponent (names rewritten to OPPONENT, --user-map), as in vsopp /
studydose. BLOCK.pgn: the same six annotated PGNs, used only for first moves.

MG = fullmove > 12, npm_light > 14, no mate score. M2 mate danger is NOT
removed (needs matedanger.py, ~50 min); opponents err there at the same rate,
so it should not move the me-vs-opponent gap.
Bands on cp_before: winning >= 150, level (-150, 150), losing <= -150.
Rates are standardized to Justin's pooled MG band mix, so a family that puts
him in more winning positions (higher base error rate) is not penalized.
P1 = share of moves with wp_error >= 0.15; P2 = mean max(wp_error, 0).
Intervals: game bootstrap, 5,000 draws, seed 23, games resampled jointly.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from studydose import family, first_moves  # noqa: E402

MATE = 10000
B = 5000


def load(d):
    m = pd.read_csv(os.path.join(d, "moves.csv.gz"), dtype={"block": str, "gid": str},
                    usecols=["gid", "fullmove", "npm_light", "cp_before", "wp_error"])
    m = m[(m.fullmove > 12) & (m.npm_light > 14) & (m.cp_before.abs() < MATE)].copy()
    m["band"] = np.select([m.cp_before >= 150, m.cp_before > -150], [0, 1], 2)
    m["e15"] = (m.wp_error >= 0.15).astype(float)
    m["wpl"] = m.wp_error.clip(lower=0)
    return m


def main():
    featlic, featopp, pgns = sys.argv[1], sys.argv[2], sys.argv[3:]
    g = pd.read_csv(os.path.join(featlic, "games.csv"), dtype={"block": str, "gid": str})
    if len(g) != 4691:
        sys.exit(f"GATE: expected the 4,691-game six-block run, got {len(g)}")
    fm = first_moves(pgns)
    g["fam"] = [family(c, fm.get(k, [])) for k, c in zip(g.gid, g.color)]
    me, op = load(featlic), load(featopp)
    W = me.band.value_counts(normalize=True).sort_index().to_numpy()
    print("pooled MG band mix (win/level/lose):", W.round(3), " MG moves me/opp:", len(me), len(op))
    rng = np.random.default_rng(23)

    def arrays(d, gids, col):
        t = d[d.gid.isin(gids)].groupby(["gid", "band"])[col].agg(["sum", "count"]).unstack(fill_value=0)
        t = t.reindex(gids, fill_value=0)
        return (t["sum"].reindex(columns=[0, 1, 2], fill_value=0).to_numpy(float),
                t["count"].reindex(columns=[0, 1, 2], fill_value=0).to_numpy(float))

    def std(s, n):
        return ((s / np.maximum(n, 1)) * W).sum(-1) * 100

    def group(gids, col):
        gids = list(gids)
        sm, nm = arrays(me, gids, col)
        so, no = arrays(op, gids, col)
        idx = rng.integers(0, len(gids), (B, len(gids)))
        bm, bo = std(sm[idx].sum(1), nm[idx].sum(1)), std(so[idx].sum(1), no[idx].sum(1))
        pm, po = std(sm.sum(0), nm.sum(0)), std(so.sum(0), no.sum(0))
        mix = nm.sum(0) / nm.sum()
        return dict(games=len(gids), moves=int(nm.sum()), me=pm, opp=po, D=pm - po,
                    D_lo=np.percentile(bm - bo, 2.5), D_hi=np.percentile(bm - bo, 97.5),
                    win=mix[0], lvl=mix[1], lose=mix[2]), bm, bm - bo

    for col, lab in [("e15", "P1 (wp_error >= 0.15)"), ("wpl", "P2 (mean wp lost)")]:
        print(f"\n==== {lab}")
        rows, dm, dd = {}, {}, {}
        for c in ["white", "black"]:
            rows[c], dm[c], dd[c] = group(g.gid[g.color == c], col)
        for f in ["London", "Englund-as-White", "Caro", "Englund", "other"]:
            rows[f], dm[f], dd[f] = group(g.gid[g.fam == f], col)
        print(pd.DataFrame(rows).T.astype(float).round(2).to_string())
        for a, b in [("white", "black"), ("London", "Caro"), ("London", "Englund"),
                     ("Caro", "Englund"), ("London", "Englund-as-White")]:
            for name, dist, est in [("me", dm, rows[a]["me"] - rows[b]["me"]),
                                    ("D", dd, rows[a]["D"] - rows[b]["D"])]:
                c = dist[a] - dist[b]
                p = 2 * min((c <= 0).mean(), (c >= 0).mean())
                print(f"  {name}: {a} - {b}: {est:+.2f}  95% [{np.percentile(c, 2.5):+.2f}, "
                      f"{np.percentile(c, 97.5):+.2f}]  two-sided p ~ {p:.3f}")


if __name__ == "__main__":
    main()
