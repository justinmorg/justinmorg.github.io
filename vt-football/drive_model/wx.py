"""Nearest airport weather station for every venue, and hourly observations for each season.

    python wx.py                 # every season in game_venues.csv
    python wx.py 2026            # just these seasons (the current season is always re-pulled)

Stations come from the Iowa Environmental Mesonet ASOS network lists (US states plus the
countries of overseas games). A station must have been reporting since before 2021 and still be
reporting. Each venue keeps up to 3 candidates within 40 km (sids), best first: stations that
log hourly precipitation are preferred unless one without it is more than 15 km closer, and
mountain-top sites are dropped. gamewx.py uses the first candidate with observations in the
game window. Observations are downloaded per station and season, covering only that
station's game dates, to asos/<sid>_<season>.csv (gitignored).
"""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import sys, json, math, time, urllib.request, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor

CUR = 2026


def get(u, raw=False, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'vt-football research'}), timeout=180) as r:
                b = r.read(); return b if raw else json.loads(b)
        except Exception:
            if k == tries - 1: raise
            time.sleep(3 + 3 * k)


V = pd.read_csv('venues.csv'); G = pd.read_csv('game_venues.csv')
CC = {'Ireland': 'IE', 'England': 'GB', 'United Kingdom': 'GB', 'Bahamas': 'BS', 'Australia': 'AU', 'Mexico': 'MX', 'Germany': 'DE'}
nets = sorted({f'{s}_ASOS' for s in V.state.dropna()} | {f'{CC[c]}__ASOS' for c in V.country.dropna() if c in CC})
st = []
for n in nets:
    try:
        for f in get(f'https://mesonet.agron.iastate.edu/geojson/network/{n}.geojson')['features']:
            p = f['properties']; lo, la = f['geometry']['coordinates']
            st.append(dict(sid=p['sid'], la=la, lo=lo, begin=p.get('archive_begin'), end=p.get('archive_end'), elev=p.get('elevation'),
                           phour=(p.get('attributes') or {}).get('HAS_PHOUR') == '1'))
    except Exception as e: print('net fail', n, e)
S = pd.DataFrame(st).drop_duplicates('sid')
S = S[S.end.isna() & (pd.to_datetime(S.begin, errors='coerce') < '2021-06-01')].reset_index(drop=True)


def near(r):
    """Up to 3 candidate stations within 40 km, best first: hourly-precip stations unless one
    without is >15 km closer; mountain-top sites (>400 m above the lowest of the 5 nearest) out."""
    if pd.isna(r.lat): return pd.Series([None, None, None])
    d = np.hypot((S.la - r.lat) * 111, (S.lo - r.lon) * 111 * math.cos(math.radians(r.lat)))
    o = d.sort_values(); low = S.elev[o.index[:5]].min()
    o = o[(S.elev[o.index].fillna(low) <= low + 400) & (o <= 40)]
    if o.empty: o = d.sort_values().head(1)
    score = o + np.where(S.phour[o.index], 0, 15)
    pick = score.sort_values().index[:3]
    return pd.Series([S.loc[pick[0], 'sid'], round(d[pick[0]], 1), ';'.join(S.loc[pick, 'sid'])])


V[['sid', 'km', 'sids']] = V.apply(near, axis=1); V.to_csv('venues.csv', index=False)
print(V.km.describe().round(1)); print(V.sort_values('km', ascending=False).head(6)[['vname', 'city', 'state', 'sid', 'km']])

seasons = [int(a) for a in sys.argv[1:]] or sorted(G.season.unique())
G = G.merge(V[['venue', 'sids', 'roof']], on='venue', how='left')
G = G[G.sids.notna()].assign(sid=G.sids.str.split(';')).explode('sid')   # all candidates
G['day'] = pd.to_datetime(G.kick, utc=True)
os.makedirs('asos', exist_ok=True)
jobs = []
for (sid, season), gg in G[G.season.isin(seasons) & G.sid.notna() & G.roof.fillna('').eq('')].groupby(['sid', 'season']):
    a = gg.day.min() - pd.Timedelta('1D'); b = gg.day.max() + pd.Timedelta('2D')
    jobs.append((sid, season, a, b))


def pull(job):
    sid, season, a, b = job; p = f'asos/{sid}_{season}.csv'
    if os.path.exists(p) and os.path.getsize(p) > 100 and season != CUR: return
    u = ('https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=' + sid +
         '&data=tmpf&data=sknt&data=gust&data=p01i&data=wxcodes'
         f'&year1={a.year}&month1={a.month}&day1={a.day}&year2={b.year}&month2={b.month}&day2={b.day}'
         '&tz=Etc/UTC&format=onlycomma&missing=M&trace=0.0001&report_type=3')
    try: open(p, 'wb').write(get(u, True))
    except Exception as e: print('pull fail', sid, season, repr(e)[:80])


with ThreadPoolExecutor(4) as ex: list(ex.map(pull, jobs))
print('station-seasons', len(jobs), 'files', len(os.listdir('asos')))
