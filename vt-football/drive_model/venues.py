"""Venues for every game in drives/games_<season>.csv (all seasons), geocoded, roofs flagged.

    python venues.py

Coordinates already in venues.csv are reused, so only new venues hit the geocoder (Open-Meteo,
no key). It drops a share of requests, so each call retries with backoff, and venues that still
fail are retried in a second pass. roof: 'dome' (fixed roof), 'retractable', or blank (open air).
Retractable roofs are treated as closed (calm and dry) downstream; nearly every college game in
one is a bowl or title game played with the roof shut, and an open roof means mild weather anyway.
Writes venues.csv and game_venues.csv (eid, season, kick UTC, venue).
"""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import glob, json, re, time, urllib.parse, urllib.request
import pandas as pd

ST = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'District of Columbia'}
CC = {'USA': 'US', 'US': 'US', 'Ireland': 'IE', 'England': 'GB', 'United Kingdom': 'GB', 'Bahamas': 'BS',
      'Australia': 'AU', 'Mexico': 'MX', 'Germany': 'DE'}
# Name fragments (case-insensitive). ESPN uses current sponsor names, so old and new names are both listed.
DOME = ['Dome', 'Ford Field', 'Allegiant', 'Superdome', 'Tropicana', 'Carrier', 'JMA', 'U.S. Bank',
        'SoFi', 'Ford Center', 'Holt Arena', 'Kibbie', 'Georgia Dome', 'Caesars']
RETRACT = ['Lucas Oil', 'AT&T Stadium', 'NRG', 'Reliant', 'State Farm Stadium', 'University of Phoenix',
           'Mercedes-Benz', 'Chase Field', 'Globe Life Field', 'loanDepot', 'Marlins Park', 'Minute Maid',
           'Daikin Park', 'American Family Field', 'T-Mobile Park', 'Rogers Centre']


def roof(name):
    n = (name or '').lower()
    if any(k.lower() in n for k in RETRACT): return 'retractable'
    if any(k.lower() in n for k in DOME): return 'dome'
    return ''


def get(u, tries=6):
    for k in range(tries):  # the geocoder drops a share of requests; back off and retry
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'vt-football research'}), timeout=60) as r:
                return json.load(r)
        except Exception:
            if k == tries - 1: raise
            time.sleep(2 + 3 * k)


def geocode(city, state, country):
    cc = CC.get(country or 'USA', '')
    city = re.sub(r'\s*\(.*\)', '', city or '')
    res = get('https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode(
        dict(name=city, count=20, countryCode=cc) if cc else dict(name=city, count=20))).get('results') or []
    if not res: raise ValueError('no match')
    want = ST.get(state, state)
    m = [x for x in res if want and x.get('admin1') == want] or res
    return m[0]['latitude'], m[0]['longitude']


G = pd.concat([pd.read_csv(f).assign(season=int(re.search(r'(\d{4})', f).group(1)))
               for f in sorted(glob.glob('drives/games_*.csv'))], ignore_index=True)
V = G.sort_values('season').drop_duplicates('venue', keep='last')[['venue', 'vname', 'city', 'state', 'country']].copy()
old = pd.read_csv('venues.csv').set_index('venue') if os.path.exists('venues.csv') else pd.DataFrame()
V['lat'] = V.venue.map(old.lat) if len(old) else None
V['lon'] = V.venue.map(old.lon) if len(old) else None
V['roof'] = V.vname.apply(roof); V['dome'] = V.roof != ''   # 'dome' kept for older scripts
for p in range(2):                                          # second pass catches stragglers
    for i in V.index[V.lat.isna()]:
        r = V.loc[i]
        try: V.loc[i, ['lat', 'lon']] = geocode(r.city, r.state, r.country)
        except Exception as e: print('geo fail', p, r.vname, r.city, r.state, repr(e)[:80])
        time.sleep(0.3)
keep = [c for c in ['sid', 'km'] if c in old.columns]
for c in keep: V[c] = V.venue.map(old[c])   # wx.py re-checks the station for every venue
V.to_csv('venues.csv', index=False)
G[['eid', 'season', 'kick', 'venue', 'vname']].to_csv('game_venues.csv', index=False)
print(len(V), 'venues;', (V.roof == 'dome').sum(), 'domes,', (V.roof == 'retractable').sum(), 'retractable')
print(V[V.roof != ''][['vname', 'roof']].to_string(index=False))
print('not geocoded:', V[V.lat.isna()].vname.tolist())
