"""Rank VT's defense by season, 1987 on: opponent-adjusted points allowed plus play-level stats.

Usage:  python defense_rank.py      (needs data/howell/games.csv from howell.py)

Adjusted defense: per season, every I-A game's two scores are fit (ridge, lambda 2, sparse
least squares) as league mean + scoring offense + scoring defense + home field (half the
home edge each way). Non-I-A opponents are pooled as one team per season. vtAdjDef is
points per game vs. an average I-A defense (negative = better); rank/of/pct/z are among
teams with 6+ games. Seasons through the last completed one come from Howell; the current
season from data/espn/games/<season>.parquet.

Limits: scores include return and defensive TDs, and short fields from VT's own turnovers
count against the defense. drive_model/team_ratings.csv (2016 on) adjusts for field
position and possessions and is the better measure where it exists.

Play stats (VT games only, data/unified): yards per scrimmage play allowed, success rate
allowed (50/70/100% of distance on 1st/2nd/3rd-4th down), 20+ yard play rate, sack rate,
rush yards per carry, and how many games have play-by-play.

Writes data/derived/vt_defense_by_season.csv.
"""
import glob, os
import numpy as np
import pandas as pd
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import lsqr

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
VT = "VirginiaTech"


def games():
    g = pd.read_csv(os.path.join(D, "howell", "games.csv"))
    last = g.season.max()
    rows = []
    for f in sorted(glob.glob(os.path.join(D, "espn", "games", "*.parquet"))):
        e = pd.read_parquet(f)
        s = int(e.season.iloc[0])
        if s <= last:
            continue
        for x in e[e.completed].itertuples():
            h = x.homeTeam if x.homeFBS else "NONIA"
            a = x.awayTeam if x.awayFBS else "NONIA"
            rows.append(dict(season=s, team=h, opp=a, pf=x.homePoints, pa=x.awayPoints,
                             home=0 if x.neutralSite else 1))
    e = pd.DataFrame(rows).replace({"Virginia Tech": VT})
    return pd.concat([g, e], ignore_index=True)


def fit(d, lam=2.0):
    teams = sorted(set(d.team) | set(d.opp))
    ix = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    obs = [(r.team, r.opp, r.pf, r.home) for r in d.itertuples()] + \
          [(r.opp, r.team, r.pa, -r.home) for r in d.itertuples()]
    m = len(obs)
    A = lil_matrix((m + 2 * n, 2 * n + 2))
    y = np.zeros(m + 2 * n)
    for k, (o, df, p, h) in enumerate(obs):
        A[k, ix[o]] = 1; A[k, n + ix[df]] = 1; A[k, 2 * n] = 1; A[k, 2 * n + 1] = h / 2
        y[k] = p
    for i in range(2 * n):
        A[m + i, i] = lam
    sol = lsqr(A.tocsr(), y)[0]
    dfn = pd.Series(sol[n:2 * n], index=teams).drop("NONIA", errors="ignore")
    cnt = pd.concat([d.team, d.opp]).value_counts()
    return sol[2 * n], dfn[cnt[dfn.index] >= 6]


def adjusted():
    out = []
    for s, d in games().groupby("season"):
        mu, dfn = fit(d)
        if VT not in dfn:
            continue
        rk = int(dfn.rank()[VT]); v = dfn[VT]
        vt = pd.concat([d[d.team == VT].pa, d[d.opp == VT].pf])
        out.append(dict(season=s, games=len(vt), ppgAllowed=round(vt.mean(), 1),
                        lgPPG=round(mu, 1), vtAdjDef=round(v, 1), rank=rk, of=len(dfn),
                        pct=round(100 * (1 - (rk - 1) / len(dfn)), 1),
                        z=round((v - dfn.mean()) / dfn.std(), 2)))
    return pd.DataFrame(out).set_index("season")


def plays():
    p = pd.concat([pd.read_parquet(f) for f in glob.glob(os.path.join(D, "unified", "plays", "*.parquet"))],
                  ignore_index=True)
    d = p[~p.vtOffense].copy()
    need, y = d.distance.astype(float), d.yards
    d["succ"] = ((d.down == 1) & (y >= 0.5 * need)) | ((d.down == 2) & (y >= 0.7 * need)) | \
                ((d.down >= 3) & (y >= need))
    d["exp"] = y >= 20
    d["sack"] = d.category == "sack"
    s = d.groupby("season").agg(ypp=("yards", "mean"), successRate=("succ", "mean"),
                                explosiveRate=("exp", "mean"), sackRate=("sack", "mean"))
    s["rushYpc"] = d[d.category == "rush"].groupby("season").yards.mean()
    s["gamesWithPbp"] = d.groupby("season").gameKey.nunique()
    return s.round(3)


if __name__ == "__main__":
    t = adjusted().join(plays())
    dm = os.path.join(HERE, "drive_model", "team_ratings.csv")
    if os.path.exists(dm):
        r = pd.read_csv(dm)
        r["driveRank"] = r.groupby("season").dfn.rank().astype(int)
        r = r[r.team == "Virginia Tech"].set_index("season")
        t["driveModelDef"] = r.dfn.round(3)
        t["driveModelRank"] = r.driveRank
    t.to_csv(os.path.join(D, "derived", "vt_defense_by_season.csv"))
    print(t.sort_values("z").head(12).to_string())
