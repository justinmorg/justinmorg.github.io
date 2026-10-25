"""Weather effects on points per drive, pooled over 2021-2026.

    python wxpool.py

Stage 1, per season (teams change year to year):
  * expected-points curve: isotonic (non-increasing) fit of drive points on start yards-to-go,
    FBS-vs-FBS non-late drives, lightly smoothed, as in ep3.py;
  * team ratings: ridge (lambda 40) of drive points minus the curve on offense + defense + home
    field, as in vtdef.py, FCS teams pooled.
Stage 2, pooled: each FBS-vs-FBS game's mean residual per drive (points - curve - ratings) is
regressed, weighted by drives, on weather terms with a season intercept. Errors come from a
bootstrap over games (2,000 draws). A joint fit (ratings refit on weather-adjusted points,
alternating to convergence) checks that the ratings did not soak up weather at windy home parks.

Writes ep_curves.csv, team_ratings.csv, game_resid.csv, wx_effects.csv, wx_bands.csv.
"""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import dm

LAM, NB = 40, 2000
BANDS = [0, 10, 15, 20, 25, 999]; BLAB = ['0-10', '10-15', '15-20', '20-25', '25+']
rng = np.random.default_rng(7)


ep_curve, ratings = dm.ep_curve, dm.ratings


W = pd.read_csv('game_weather.csv').drop_duplicates('eid').set_index('eid')
drives, curves, rat = [], [], []
for s in dm.SEASONS:
    g = dm.games(s); fbs = dm.fbs_teams(g)
    D = dm.clean(pd.read_parquet(f'drives/{s}.parquet'), fbs); D['season'] = s
    fbsfbs = (D.offT != 'FCS') & (D.dfnT != 'FCS')
    cur = ep_curve(D[~D.late & fbsfbs]); curves.append(cur.rename(s))
    D['ep'] = D.ytg.round().clip(1, 99).astype(int).map(cur).values
    A = D[~D.late].copy()
    R, h, fitted = ratings(A, (A.pts - A.ep).values)
    A['rat'] = fitted; A['res'] = A.pts - A.ep - A.rat; A['fbsfbs'] = fbsfbs[A.index]
    rat.append(R.assign(season=s, home=h)); drives.append(A)
    print(s, 'drives', len(A), 'pts/drive', round(A.pts.mean(), 3), 'curve @75', round(cur[75], 2), '@50', round(cur[50], 2), '@30', round(cur[30], 2), 'home', round(h, 3))
A = pd.concat(drives, ignore_index=True)
pd.concat(curves, axis=1).round(4).rename_axis('ytg').to_csv('ep_curves.csv')
pd.concat(rat).round(4).to_csv('team_ratings.csv', index=False)

# game-level table (FBS vs FBS, outdoor or indoor, weather known)
G = (A[A.fbsfbs].groupby('eid').agg(season=('season', 'first'), drives=('res', 'size'), pts=('pts', 'sum'),
                                     ep=('ep', 'sum'), rat=('rat', 'sum'), res=('res', 'mean')))
G = G.join(W[['vname', 'wind', 'gust', 'rain', 'precip', 'temp', 'dome']], how='inner')
G = G[G.wind.notna()].copy()
G['indoor'] = (G.dome == 1).astype(int)
G['band'] = np.where(G.indoor == 1, 'indoor', pd.cut(G.wind, BANDS, right=False, labels=BLAB).astype(str))
G['cold'] = ((G.temp < 40) & (G.indoor == 0)).astype(int)
G['rainy'] = G.rain.where(G.indoor == 0, 0)
G.round(4).to_csv('game_resid.csv')
print('\ngames used', len(G), 'drives', int(G.drives.sum()))

seas = pd.get_dummies(G.season, prefix='s', dtype=float)


def design(G, spec, T=None):
    X = pd.DataFrame(index=G.index)
    if spec == 'bands':
        for b in BLAB[1:]: X['w' + b] = (G.band == b).astype(float)
    else:
        X[f'wind>{T}'] = np.clip(G.wind - T, 0, None) * (1 - G.indoor)
    X['indoor'] = G.indoor; X['rain'] = G.rainy; X['cold<40'] = G.cold
    return pd.concat([X, seas.loc[G.index]], axis=1)


def wls(X, y, w):
    sw = np.sqrt(w); return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def fit_boot(spec, T=None, G=G):
    X = design(G, spec, T); y = G.res.values; w = G.drives.values.astype(float)
    b = wls(X.values, y, w); k = [c for c in X.columns if not c.startswith('s_')]
    n = len(G); bs = []
    for _ in range(NB):
        i = rng.integers(0, n, n); bs.append(wls(X.values[i], y[i], w[i]))
    bs = np.array(bs)
    out = pd.DataFrame(dict(term=k, est=b[:len(k)], se=bs[:, :len(k)].std(0),
                            lo=np.percentile(bs[:, :len(k)], 2.5, 0), hi=np.percentile(bs[:, :len(k)], 97.5, 0)))
    sse = np.sum(w * (y - X.values @ b) ** 2)
    return out, sse


# 1) wind bands
eb, sse_b = fit_boot('bands')
cnt = G.groupby('band').agg(games=('res', 'size'), drives=('drives', 'sum'), raw_ppd=('pts', 'sum'))
cnt['raw_ppd'] /= cnt.drives
cnt['exp_ppd'] = G.groupby('band').apply(lambda x: (x.ep.sum() + x.rat.sum()) / x.drives.sum(), include_groups=False)
cnt['resid_ppd'] = G.groupby('band').apply(lambda x: np.average(x.res, weights=x.drives), include_groups=False)
cnt = cnt.reindex(BLAB + ['indoor'])
eb['games'] = eb.term.map(lambda t: cnt.games.get(t[1:], np.nan) if t.startswith('w') else
                          {'indoor': G.indoor.sum(), 'rain': (G.rainy >= 0.5).sum(), 'cold<40': G.cold.sum()}[t])
print('\nWIND BANDS (pts/drive vs outdoor 0-10 mph; rain = all observations wet; season intercepts)')
print(eb.round(3).to_string(index=False)); print(cnt.round(3).to_string())

# 2) threshold (hinge): slope per mph above T, T chosen by fit
prof = []
for T in [8, 10, 12, 14, 15, 16, 18, 20, 22]:
    e, sse = fit_boot('hinge', T) if T in (10, 15, 20) else (None, None)
    if sse is None:
        X = design(G, 'hinge', T); b = wls(X.values, G.res.values, G.drives.values.astype(float))
        sse = np.sum(G.drives.values * (G.res.values - X.values @ b) ** 2)
    prof.append((T, sse))
prof = pd.DataFrame(prof, columns=['T', 'sse']); prof['d_sse'] = prof.sse - prof.sse.min()
Tbest = int(prof.loc[prof.sse.idxmin(), 'T'])
print('\nthreshold profile (weighted SSE above best):'); print(prof.round(2).to_string(index=False))
# bootstrap the threshold choice itself
Tgrid = prof['T'].tolist(); tb = []
for _ in range(400):
    i = rng.integers(0, len(G), len(G)); Gi = G.iloc[i]
    ss = []
    for T in Tgrid:
        X = design(Gi, 'hinge', T).reindex(columns=design(G, 'hinge', T).columns, fill_value=0)
        b = wls(X.values, Gi.res.values, Gi.drives.values.astype(float))
        ss.append(np.sum(Gi.drives.values * (Gi.res.values - X.values @ b) ** 2))
    tb.append(Tgrid[int(np.argmin(ss))])
tb = pd.Series(tb).value_counts(normalize=True).sort_index()
print('bootstrap share choosing each threshold:', tb.round(2).to_dict())
eh, _ = fit_boot('hinge', Tbest)
eh15, _ = fit_boot('hinge', 15)
print(f'\nTHRESHOLD T={Tbest}'); print(eh.round(3).to_string(index=False))
print('THRESHOLD T=15'); print(eh15.round(3).to_string(index=False))

# 3) joint check: ratings refit on weather-adjusted points (backfitting), bands spec
X = design(G, 'bands'); kb = [c for c in X.columns if not c.startswith('s_')]
wx_game = pd.Series(0.0, index=G.index)
for it in range(8):
    parts = []
    for s in dm.SEASONS:
        As = A[A.season == s].copy()
        adj = As.eid.map(wx_game).fillna(0).values
        _, _, fitted = ratings(As, (As.pts - As.ep).values - adj)
        As['res2'] = As.pts - As.ep - fitted; parts.append(As)
    A2 = pd.concat(parts)
    G['res2'] = A2[A2.fbsfbs].groupby('eid').res2.mean().reindex(G.index)
    b = wls(X.values, G.res2.values, G.drives.values.astype(float))
    new = pd.Series(X[kb].values @ b[:len(kb)], index=G.index)
    if np.abs(new - wx_game).max() < 1e-4: break
    wx_game = new
print('\njoint (backfit) band estimates:', dict(zip(kb, b[:len(kb)].round(3))), 'iterations', it + 1)

eb['spec'] = 'bands'; eh['spec'] = f'threshold_{Tbest}'; eh15['spec'] = 'threshold_15'
pd.concat([eb, eh, eh15]).round(4).to_csv('wx_effects.csv', index=False)
cnt.round(4).rename_axis('band').to_csv('wx_bands.csv')
