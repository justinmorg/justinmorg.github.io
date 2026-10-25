"""Weather from 30 minutes before kickoff to 3.5 hours after, for every game in game_venues.csv.

    python gamewx.py

wind = mean sustained wind (mph), gust = max gust (mph; max sustained if no gusts logged),
precip = inches, rain = share of observations with rain, drizzle, snow or storms,
temp = mean temperature (F). Domes and retractable roofs are calm, dry, 70 F (roof column says
which). Uses the first of the venue's candidate stations (wx.py) with 2+ observations in the
window; games with none are left blank.
Writes game_weather.csv.
"""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np

V = pd.read_csv('venues.csv').set_index('venue'); G = pd.read_csv('game_venues.csv')
cache = {}


def obs(sid, season):
    k = (sid, season)
    if k not in cache:
        p = f'asos/{sid}_{season}.csv'
        df = pd.read_csv(p, na_values='M', low_memory=False) if os.path.exists(p) and os.path.getsize(p) > 100 else None
        if df is not None:
            df['valid'] = pd.to_datetime(df.valid, utc=True)
            for c in ['tmpf', 'sknt', 'gust', 'p01i']: df[c] = pd.to_numeric(df[c], errors='coerce')
        cache[k] = df
    return cache[k]


rows = []
for g in G.itertuples():
    v = V.loc[g.venue] if g.venue in V.index else None
    r = dict(eid=g.eid, season=g.season, vname=g.vname)
    if v is None: rows.append(r); continue
    if isinstance(v.roof, str) and v.roof:
        r.update(wind=0, gust=0, precip=0, rain=0, temp=70, dome=1, roof=v.roof); rows.append(r); continue
    if pd.isna(v.sids): rows.append(r); continue
    k = pd.Timestamp(g.kick); w = None
    for sid in v.sids.split(';'):                 # first candidate station with data in the window
        df = obs(sid, g.season)
        if df is None: continue
        w = df[(df.valid >= k - pd.Timedelta('30min')) & (df.valid <= k + pd.Timedelta('3.5h'))]
        if len(w) >= 2 and w.sknt.notna().sum() >= 2: break
        w = None
    if w is None: rows.append(r); continue
    wx = w.wxcodes.fillna('').astype(str)
    r.update(sid=sid, wind=w.sknt.mean() * 1.151,
             gust=(w.gust.max() if w.gust.notna().any() else w.sknt.max()) * 1.151,
             precip=w.p01i.fillna(0).clip(lower=0).sum(), rain=wx.str.contains('RA|DZ|SN|TS').mean(),
             temp=w.tmpf.mean(), dome=0, roof='')
    rows.append(r)
W = pd.DataFrame(rows); W.to_csv('game_weather.csv', index=False, float_format='%.3f')
print(W.groupby('season').agg(games=('eid', 'size'), missing=('wind', lambda s: s.isna().sum()),
                               indoor=('dome', 'sum'), wind=('wind', 'mean'), cold=('temp', lambda t: (t < 40).sum())).round(2))
print(W.sort_values('wind', ascending=False).head(10).round(1).to_string(index=False))
