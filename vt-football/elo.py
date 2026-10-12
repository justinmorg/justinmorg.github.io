"""Elo ratings for every FBS (and FCS-opponent) team, rebuilt from ESPN results (espn.py).

Replaces CFBD's pregame Elo when that's stale or over quota. Model (FiveThirtyEight-style):
  * expected home win prob  E = 1 / (1 + 10^(-(Rh + HFA*not_neutral - Ra) / 400))
  * update  dR = K * MOV * (S - E),  MOV = ln(|margin| + 1) * 2.2 / (0.001 * winner_edge + 2.2)
    (winner_edge = winner's pregame Elo advantage incl. home field; damps runaway favorites)
  * new season: every rating regressed a fraction R toward its division mean
    (FBS 1500, non-FBS 1200); first-seen FBS teams start at 1500, others at 1200.
  * Elo point spread = Elo edge / PTS (PTS fit on past games: points per Elo point).
K, HFA, R are tuned on 2014-2025 FBS-vs-FBS log loss (2010-2013 is burn-in): `python elo.py --tune`.

Usage:
    python elo.py            # build data/elo/games.parquet and data/elo/ratings_current.csv
    python elo.py --tune     # grid search K, HFA, R
"""
import glob, itertools, math, os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "elo")
TUNED = dict(K=35, HFA=55, R=0.2)   # from --tune (Oct 2026): log loss 0.5526 on 2014-2025


def load():
    g = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(HERE, "data", "espn", "games", "*.parquet")))])
    return g.sort_values(["date", "eventId"]).reset_index(drop=True)


def run(g, K, HFA, R):
    rating, fbs_of, season_seen = {}, {}, None
    pre_h, pre_a, prob = [], [], []
    for row in g.itertuples(index=False):
        if row.season != season_seen:
            for t in rating:
                mean = 1500 if fbs_of.get(t) else 1200
                rating[t] = mean + (rating[t] - mean) * (1 - R)
            season_seen = row.season
        for tid, f in ((row.homeId, row.homeFBS), (row.awayId, row.awayFBS)):
            fbs_of[tid] = f
            if tid not in rating: rating[tid] = 1500.0 if f else 1200.0
        rh, ra = rating[row.homeId], rating[row.awayId]
        edge = rh - ra + (0 if row.neutralSite else HFA)
        e = 1 / (1 + 10 ** (-edge / 400))
        pre_h.append(rh); pre_a.append(ra); prob.append(e)
        if not row.completed or pd.isna(row.homePoints): continue
        m = row.homePoints - row.awayPoints
        s = 1.0 if m > 0 else 0.0 if m < 0 else 0.5
        win_edge = edge if m > 0 else -edge
        mov = math.log(abs(m) + 1) * 2.2 / (0.001 * win_edge + 2.2)
        d = K * mov * (s - e)
        rating[row.homeId] = rh + d; rating[row.awayId] = ra - d
    out = g.copy()
    out["homeElo"], out["awayElo"], out["homeWinProb"] = pre_h, pre_a, prob
    out["eloEdge"] = out.homeElo - out.awayElo + np.where(out.neutralSite, 0, HFA)
    return out, rating, fbs_of


def score(df):
    x = df[df.completed & df.homeFBS & df.awayFBS & (df.season >= 2014) & (df.season <= 2025)
           & (df.homePoints != df.awayPoints)]
    y = (x.homePoints > x.awayPoints).astype(float); p = x.homeWinProb.clip(1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()


def tune(g):
    res = []
    for k, h, r in itertools.product([20, 25, 30, 35, 40, 50], [40, 55, 70, 85], [0.2, 0.33, 0.5]):
        res.append((score(run(g, k, h, r)[0]), k, h, r))
        print(f"K={k} HFA={h} R={r}: log loss {res[-1][0]:.4f}")
    best = min(res); print("best:", best); return best


def main(argv):
    g = load()
    if "--tune" in argv:
        tune(g); return
    df, rating, fbs_of = run(g, **TUNED)
    done = df[df.completed & df.homeFBS & df.awayFBS & (df.season <= 2025)]
    pts = np.polyfit(done.eloEdge, done.homePoints - done.awayPoints, 1)[0]
    df["eloHomeSpread"] = -(df.eloEdge * pts).round(1)   # negative = home favored, like a line
    os.makedirs(OUT, exist_ok=True)
    df.to_parquet(os.path.join(OUT, "games.parquet"), index=False)
    names = pd.concat([g[["homeId", "homeTeam"]].set_axis(["id", "team"], axis=1),
                       g[["awayId", "awayTeam"]].set_axis(["id", "team"], axis=1)]).drop_duplicates("id", keep="last").set_index("id").team
    cur = pd.DataFrame({"team": [names[t] for t in rating], "elo": [round(v, 1) for v in rating.values()],
                        "fbs": [bool(fbs_of[t]) for t in rating]}).sort_values("elo", ascending=False)
    cur = cur[cur.fbs].drop(columns="fbs"); cur.insert(0, "rank", range(1, len(cur) + 1))
    cur.to_csv(os.path.join(OUT, "ratings_current.csv"), index=False)
    print(f"{len(df)} games; points per Elo point {pts:.4f} (1 point = {1/pts:.1f} Elo)")
    print(cur.head(10).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:])
