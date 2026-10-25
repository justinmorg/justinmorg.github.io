"""VT's 2026 defense re-scored with the multi-season weather terms (run wxpool.py first).

    python vtwx.py

Weather coefficients are refit from game_resid.csv with VT's own 2026 games left out (so Boston
College's 30 mph game doesn't help set the penalty it then receives), in two forms:
  bands  - wind bands (10-15, 15-20, 20-25, 25+ mph vs 0-10) + rain share + cold (<40 F) + indoor
  linear - points per drive per mph of wind above 8 mph + the same rain/cold/indoor terms
2026 team ratings are refit on weather-adjusted drive points (so a team's offense isn't marked
down for its own wind games), leaving the VT game being scored out, as in vtdef.py. Expected
points = sum over the opponent's non-late drives of curve + offense rating + home field + weather.
Weather uncertainty: 1,000 bootstrap draws of the weather fit (over games).
Writes vt_def_wx.csv.
"""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import dm

BLAB = ['0-10', '10-15', '15-20', '20-25', '25+']; T = 8; NB = 1000; VT = 'Virginia Tech'
rng = np.random.default_rng(11)


def wx_terms(df, spec):
    """Weather design for games (needs band/wind/indoor/rainy/cold)."""
    X = pd.DataFrame(index=df.index)
    if spec == 'bands':
        for b in BLAB[1:]: X['w' + b] = (df.band == b).astype(float)
    else:
        X[f'wind>{T}'] = np.clip(df.wind - T, 0, None) * (1 - df.indoor)
    X['indoor'] = df.indoor.astype(float); X['rain'] = df.rainy; X['cold<40'] = df.cold.astype(float)
    return X


def wfit(G, spec):
    X = pd.concat([wx_terms(G, spec), pd.get_dummies(G.season, prefix='s', dtype=float)], axis=1)
    sw = np.sqrt(G.drives.values.astype(float))
    b = np.linalg.lstsq(X.values * sw[:, None], G.res.values * sw, rcond=None)[0]
    k = wx_terms(G.head(1), spec).columns
    return pd.Series(b[:len(k)], index=k)


# --- weather fits without VT's 2026 games ---------------------------------------------------
GR = pd.read_csv('game_resid.csv', index_col=0)
g26 = dm.games(2026)
vt_eids = set(g26.index[(g26.homeTeam == VT) | (g26.awayTeam == VT)])
Gx = GR[~GR.index.isin(vt_eids)]
coef = {s: wfit(Gx, s) for s in ('bands', 'linear')}
boot = {s: [] for s in coef}
for _ in range(NB):
    Gi = Gx.iloc[rng.integers(0, len(Gx), len(Gx))]
    for s in coef: boot[s].append(wfit(Gi, s).reindex(coef[s].index, fill_value=0))
for s in coef: print(s, coef[s].round(3).to_dict())

# --- weather for every 2026 game (all games, incl. FCS opponents) ----------------------------
W = pd.read_csv('game_weather.csv').drop_duplicates('eid').set_index('eid')
W = W[W.season == 2026].copy()
W['indoor'] = (W.dome == 1).astype(int)
W['band'] = np.where(W.indoor == 1, 'indoor', pd.cut(W.wind, [0, 10, 15, 20, 25, 999], right=False, labels=BLAB).astype(str))
W['cold'] = ((W.temp < 40) & (W.indoor == 0)).astype(int); W['rainy'] = W.rain.where(W.indoor == 0, 0)
WX = {s: wx_terms(W[W.wind.notna()], s) for s in coef}

# --- 2026 drives, curve, weather-adjusted ratings (leave the scored game out) ----------------
D = dm.clean(pd.read_parquet('drives/2026.parquet'), dm.fbs_teams(g26))
cur = pd.read_csv('ep_curves.csv', index_col='ytg')['2026']
D['ep'] = D.ytg.round().clip(1, 99).astype(int).map(cur).values
A = D[~D.late].reset_index(drop=True)


def game_wx(spec, b):
    return (WX[spec] @ b).reindex(A.eid.unique()).fillna(0)   # per-drive effect by game


def score(spec, b):
    gw = game_wx(spec, b); adj = A.eid.map(gw).values
    rows = []
    for eid, gg in A[A.dfn == VT].groupby('eid'):
        m = (A.eid != eid).values
        R, h, _ = dm.ratings(A[m], (A.pts - A.ep - adj).values[m])
        off = R.set_index('team').off
        o = off.get(gg.offT.iloc[0], 0.0) + h * gg.home.iloc[0]
        rows.append(dict(eid=eid, opp=gg.off.iloc[0], drives=len(gg), pts=gg.pts.sum(), ep_fp=gg.ep.sum(),
                         off_adj=o * len(gg), wx=gw[eid] * len(gg)))
    r = pd.DataFrame(rows); r['exp'] = r.ep_fp + r.off_adj + r.wx; r['diff'] = r.pts - r.exp
    return r


base = score('bands', pd.Series(0.0, index=coef['bands'].index))          # no weather terms
out = base[['eid', 'opp', 'drives', 'pts', 'ep_fp']].copy()
out['exp_nowx'] = base.exp; out['diff_nowx'] = base['diff']
for s in coef:
    r = score(s, coef[s])
    out[f'wx_{s}'] = r.wx; out[f'exp_{s}'] = r.exp; out[f'diff_{s}'] = r['diff']
    # weather-effect uncertainty for each game (ratings held at the point fit)
    se = np.array([(WX[s] @ bb).reindex(out.eid).fillna(0).values * out.drives.values for bb in boot[s]]).std(0)
    out[f'wx_{s}_se'] = se
out = out.merge(W[['wind', 'gust', 'rain', 'temp', 'band']], left_on='eid', right_index=True, how='left')
out['date'] = out.eid.map(g26.date)
out = out.sort_values('date')
pd.set_option('display.width', 250)
cols = ['date', 'opp', 'band', 'wind', 'rain', 'temp', 'drives', 'pts', 'exp_nowx', 'diff_nowx',
        'wx_bands', 'wx_bands_se', 'diff_bands', 'wx_linear', 'wx_linear_se', 'diff_linear']
print(out[cols].round(2).to_string(index=False))
tot = out[['drives', 'pts', 'diff_nowx', 'diff_bands', 'diff_linear']].sum()
print('\nseason totals:', tot.round(1).to_dict())
for c in ['diff_nowx', 'diff_bands', 'diff_linear']:
    print(f'  {c}: {tot[c] / tot.drives:+.3f} pts/drive; excluding BC {out[out.opp != "Boston College"][c].sum() / out[out.opp != "Boston College"].drives.sum():+.3f}')

# season-long VT defensive rating with and without weather (all games, FBS rank)
for s in ['none'] + list(coef):
    adj = 0 if s == 'none' else A.eid.map(game_wx(s, coef[s])).values
    R, h, _ = dm.ratings(A, (A.pts - A.ep - adj).values)
    R = R[R.team != 'FCS'].set_index('team')
    print(f'VT defense pts/drive vs average ({s}): {R.dfn[VT]:+.3f}, rank {int(R.dfn.rank()[VT])} of {len(R)}')
out.round(3).to_csv('vt_def_wx.csv', index=False)
