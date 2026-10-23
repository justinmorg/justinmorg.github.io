#!/usr/bin/env python3
"""
studydose.py — opening edge over same-rated opponents, by repertoire family.
Implements studydose_prespec.md exactly; change that file first.

Usage:
    python3 studydose.py FEATLIC FEATOPP BLOCK.pgn [BLOCK.pgn ...] [--draws 10000]

FEATLIC / FEATOPP: features.py on the six settled Lichess blocks, for Justin
and for the opponent (names rewritten to OPPONENT, --user-map), as in vsopp.
BLOCK.pgn: the same six annotated PGNs, used only to read the first moves.
"""
import argparse
import os
import sys

import chess.pgn
import numpy as np
import pandas as pd

MATE_CP = 10000
FAM = ["London", "Caro", "Englund"]


def first_moves(paths):
    out = {}
    for p in paths:
        with open(p) as f:
            while True:
                g = chess.pgn.read_game(f)
                if g is None:
                    break
                b, sans = g.board(), []
                for mv in g.mainline_moves():
                    sans.append(b.san(mv)); b.push(mv)
                    if len(sans) == 6:
                        break
                out[g.headers.get("GameId", "")] = sans
    return out


def family(color, s):
    if len(s) < 2:
        return "other"
    if color == "white" and s[0] == "d4":
        return "Englund-as-White" if s[1] == "e5" else "London"
    if color == "black" and s[0] == "e4" and s[1] == "c6":
        if len(s) >= 5 and s[3] == "d5":
            return {"e5": "Caro", "exd5": "Caro"}.get(s[4], "Caro")
        return "Caro"
    if color == "black" and s[0] == "d4" and s[1] == "e5":
        return "Englund"
    return "other"


def caro_line(s):
    if len(s) >= 5 and s[3] == "d5":
        return {"e5": "Advance", "exd5": "Exchange"}.get(s[4], "Caro-other")
    return "Caro-other"


def load(d):
    m = pd.read_csv(os.path.join(d, "moves.csv.gz"), dtype={"block": str, "gid": str})
    m = m[(m.fullmove <= 12) & (m.cp_before.abs() < MATE_CP)].copy()
    m["e15"] = (m.wp_error >= 0.15).astype(float)
    m["wpl"] = m.wp_error.clip(lower=0)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("featlic"); ap.add_argument("featopp"); ap.add_argument("pgns", nargs="+")
    ap.add_argument("--draws", type=int, default=10000)
    a = ap.parse_args()

    g = pd.read_csv(os.path.join(a.featlic, "games.csv"), dtype={"block": str, "gid": str})
    go = pd.read_csv(os.path.join(a.featopp, "games.csv"), dtype={"block": str, "gid": str})
    nm = len(pd.read_csv(os.path.join(a.featlic, "moves.csv.gz"), usecols=["gid"]))
    no = len(pd.read_csv(os.path.join(a.featopp, "moves.csv.gz"), usecols=["gid"]))
    if (len(g), nm, len(go), no) != (4691, 155192, 4691, 155008):
        sys.exit(f"GATE: {len(g)}/{nm} and {len(go)}/{no}")
    if pd.to_datetime(g.date).max() >= pd.Timestamp("2026-09-03"):
        sys.exit("GATE: game in group F treatment block")

    fm = first_moves(a.pgns)
    g["fam"] = [family(c, fm.get(k, [])) for k, c in zip(g.gid, g.color)]
    g["line"] = [caro_line(fm.get(k, [])) if f == "Caro" else f for k, f in zip(g.gid, g.fam)]
    print("games by family:", g.fam.value_counts().to_dict())

    me, op = load(a.featlic), load(a.featopp)
    rng = np.random.default_rng(23)

    def per_game(d, gids, col):
        s = d[d.gid.isin(gids)].groupby("gid")[col].agg(["sum", "count"]).reindex(gids, fill_value=0)
        return s["sum"].to_numpy(float), s["count"].to_numpy(float)

    def boot(gids, col):
        sm, nm_ = per_game(me, gids, col); so, no_ = per_game(op, gids, col)
        idx = rng.integers(0, len(gids), (a.draws, len(gids)))
        d = sm[idx].sum(1) / nm_[idx].sum(1) - so[idx].sum(1) / no_[idx].sum(1)
        return dict(n_games=len(gids), n_me=int(nm_.sum()), n_opp=int(no_.sum()),
                    me=sm.sum() / nm_.sum() * 100, opp=so.sum() / no_.sum() * 100,
                    D=(sm.sum() / nm_.sum() - so.sum() / no_.sum()) * 100), d * 100

    for col, label in [("e15", "P1 (primary)"), ("wpl", "P2 (exploratory)")]:
        print(f"\n==== {label}")
        res, dist = {}, {}
        for f in FAM + ["Englund-as-White"]:
            res[f], dist[f] = boot(list(g.gid[g.fam == f]), col)
        for f in ["Advance", "Exchange"]:
            res["Caro " + f], dist["Caro " + f] = boot(list(g.gid[g.line == f]), col)
        t = pd.DataFrame(res).T
        t["lo"] = [np.percentile(dist[k], 2.5) for k in t.index]
        t["hi"] = [np.percentile(dist[k], 97.5) for k in t.index]
        print(t.round(2).to_string())
        for x, y in [("Englund", "London"), ("Caro", "London"), ("Englund", "Caro"),
                     ("Caro Advance", "Caro Exchange")]:
            c = dist[x] - dist[y]; est = res[x]["D"] - res[y]["D"]
            p = (c <= 0).mean()
            print(f"  D_{x} - D_{y}: {est:+.2f} pts  95% [{np.percentile(c, 2.5):+.2f}, "
                  f"{np.percentile(c, 97.5):+.2f}]  one-sided p = {p:.4f}  "
                  f"80%-power detectable at alpha .01 one-sided: {(2.326 + 0.842) * c.std():.2f} pts")
        o = [res[f]["D"] for f in FAM]
        print("  predicted order D_London < D_Caro < D_Englund:", o[0] < o[1] < o[2])


if __name__ == "__main__":
    main()
