"""How predictive is the rebuilt Elo? Compares it with closing spreads on FBS-vs-FBS games.

Needs data/elo/games.parquet (elo.py) and data/espn/odds/ (espn.py --odds).
Usage: python elo_backtest.py
"""
import glob, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_parquet(os.path.join(HERE, "data", "elo", "games.parquet"))
od = pd.concat([pd.read_parquet(f) for f in glob.glob(os.path.join(HERE, "data", "espn", "odds", "*.parquet"))])
x = df.merge(od, on="eventId")
x = x[x.completed & x.homeFBS & x.awayFBS & (x.season <= 2025) & (x.homePoints != x.awayPoints)].copy()
x["margin"] = x.homePoints - x.awayPoints
x["y"] = (x.margin > 0).astype(float)
x = x[x.homeSpread.abs() < 70]

# map the closing spread to a win probability with a one-parameter logistic fit
from math import log
def fit_logit(z, y):
    a = 0.1
    for _ in range(50):
        p = 1 / (1 + np.exp(-a * z)); g = ((p - y) * z).sum(); h = (p * (1 - p) * z * z).sum(); a -= g / h
    return a
a = fit_logit(-x.homeSpread.values, x.y.values)
x["vegasProb"] = 1 / (1 + np.exp(a * x.homeSpread))

def metrics(d, col):
    p = d[col].clip(1e-6, 1 - 1e-6)
    return dict(n=len(d), favWin=((p > .5) == (d.y == 1)).mean(), brier=((p - d.y) ** 2).mean(),
                logloss=-(d.y * np.log(p) + (1 - d.y) * np.log(1 - p)).mean())

def mae(d, col): return (d.margin + d[col]).abs().mean()   # spreads are home lines: margin ~ -spread

print(f"{len(x)} FBS-vs-FBS games with closing lines, {x.season.min()}-{x.season.max()}")
rows = []
for name, d in [("all", x), ("weeks 1-4", x[(x.seasonType == 'regular') & (x.week <= 4)]),
                ("weeks 5-9", x[(x.seasonType == 'regular') & x.week.between(5, 9)]),
                ("weeks 10+", x[(x.seasonType == 'regular') & (x.week >= 10)]), ("bowls/CFP", x[x.seasonType == 'post'])]:
    e, v = metrics(d, "homeWinProb"), metrics(d, "vegasProb")
    rows.append([name, e["n"], e["favWin"], v["favWin"], e["brier"], v["brier"], mae(d, "eloHomeSpread"), mae(d, "homeSpread")])
t = pd.DataFrame(rows, columns=["games", "n", "Elo fav wins", "Vegas fav wins", "Elo Brier", "Vegas Brier", "Elo MAE", "Vegas MAE"])
print(t.round(3).to_string(index=False))

dis = x[(x.homeWinProb > .5) != (x.vegasProb > .5)]
print(f"\nElo and Vegas pick different winners in {len(dis)} games ({len(dis)/len(x):.1%}); "
      f"Vegas's pick wins {((dis.vegasProb > .5) == (dis.y == 1)).mean():.1%}")
# betting Elo's side against the line
edge = (-x.eloHomeSpread) - (-x.homeSpread)              # Elo margin minus Vegas margin, home view
cover = np.sign(x.margin + x.homeSpread)                 # +1 home covers
picks = x[(edge.abs() >= 3) & (cover != 0)]
hit = (np.sign(edge[picks.index]) == cover[picks.index]).mean()
print(f"Betting Elo's side when it differs from the line by 3+ points: {hit:.1%} of {len(picks)} games (need 52.4%)")
# calibration of Elo
x["bin"] = pd.cut(x.homeWinProb, np.arange(0, 1.01, .1))
print("\nElo calibration (predicted vs actual home win %):")
print(x.groupby("bin", observed=True).agg(n=("y", "size"), predicted=("homeWinProb", "mean"), actual=("y", "mean")).round(2).to_string())
# combined
z = np.column_stack([np.log(x.homeWinProb / (1 - x.homeWinProb)), -a * x.homeSpread])
w = np.zeros(2)
for _ in range(50):
    p = 1 / (1 + np.exp(-z @ w)); g = z.T @ (p - x.y); H = (z * (p * (1 - p))[:, None]).T @ z; w -= np.linalg.solve(H, g)
print(f"\nLogistic weights when both are used: Elo {w[0]:.2f}, Vegas {w[1]:.2f} (1 = take at face value)")
