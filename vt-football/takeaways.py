"""VT defensive takeaways (interceptions + opponent fumbles lost) per game and per season.

Writes data/derived/vt_takeaways_by_game.csv and data/derived/vt_takeaways_by_season.csv.

Source per game, in order of preference:
  box        official stat-crew XML totals (hokiesports/raw/<hsGameId>.xml): opponent
             pass int + fumbles lost. Includes special-teams fumbles.
  wmt        official WMT team stats (hokiesports/raw_wmt/<id>.json).
  espn       ESPN game box (data/espn/box, from espn_box.py), 2010 on: opponent interceptions
             thrown + fumbles lost. Matches the official box in 108 of 109 VT games where both
             exist, so it outranks play text.
  teamstats  2002 West Virginia partial box score (data/stats_hokiesports/teamstats/5988).
  pbp        play text: interceptions and VT fumble recoveries on opponent scrimmage plays
             (data/unified/plays), plus opponent muffs VT recovered on VT punts/kickoffs
             (data/plays). Ambiguous recoveries were checked by hand (MANUAL_VT below).

Play text (CFBD) misses or double-counts some turnovers in 2021-2025 (e.g. a penalty-nullified
INT, a duplicated INT, missing INTs), which is why ESPN is preferred where it exists.

Check: on the 188 games with both an official box and CFBD plays, box INTs match CFBD
exactly in 98% of games; the play-text method alone misses special-teams fumbles, which is
why the box is preferred.
"""
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
VT_TOKENS = {'VT', 'VTech', 'Hokies', 'VaTch', 'Virginia Tech'}
VT_START = re.compile(r'(VT|VTech|Hokies|VaTch)\b')

# Recoveries whose text names only a player (or "Team"); resolved by roster or next possession.
MANUAL_VT = [
    'Mike Daniels (VT)', 'Aaron Rouse at the WVirg 24', 'recovered by Vince Hall',
    'recovered by Xavier Adibi', 'Noland Burchette at the VaTch 5', 'recovered by Carlton Powell',
    'recovered by Tory Harrison', 'recovered by Roland Minor', 'recovered by Barry Booker',
    'recovered by Chris Ellis at the UVa', 'recovered by Kam Chancellor', 'recovered by Cam Martin',
    'Garbutt 16 Yd Fumble Return', 'recovered by Team at the Ohio 8',
]


def last_recovery(text):
    m = re.findall(r'recovered by\s+(?:the\s+)?(?:#\d+\s+)?([A-Za-z.&\'-]+)(\s+Tech)?', text)
    return (m[-1][0] + m[-1][1]) if m else None


def pbp_counts():
    plays = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob(f'{D}/unified/plays/*.parquet')))
    d = plays[~plays.vtOffense].copy()
    # Drop the original call on overturned replays.
    d['text'] = d.text.fillna('').str.split(r'\(Original Play', regex=True).str[0]
    d['INT'] = d.category.eq('int')

    def vt_recovered(r):
        if r.INT or not r.fumble or not re.search('fumbl', r.text, re.I):
            return False
        if any(m in r.text for m in MANUAL_VT):
            return True
        tok = last_recovery(r.text)
        return tok in VT_TOKENS

    d['FUM'] = d.apply(vt_recovered, axis=1)
    g = d.groupby('gameKey')[['INT', 'FUM']].sum()

    kick = {}
    for f in glob.glob(f'{D}/plays/*.parquet'):
        p = pd.read_parquet(f)
        for _, r in p[p.offense == 'Virginia Tech'].iterrows():
            t = r.playText if isinstance(r.playText, str) else ''
            pt = r.playType if isinstance(r.playType, str) else ''
            if not (re.search('Punt|Kickoff', pt) or re.search(r'\bpunt|kickoff', t, re.I)):
                continue
            if not re.search('fumbl|muff', t, re.I):
                continue
            recs = re.findall(r'recovered by\s+(?:the\s+)?(\S+)', t)
            if recs and VT_START.match(recs[-1]):
                kick[str(r.gameId)] = kick.get(str(r.gameId), 0) + 1
    return g, kick


def box_counts():
    out = {}
    for f in glob.glob(os.path.join(HERE, 'hokiesports/raw/*.xml')):
        for t in ET.parse(f).getroot().iter('team'):
            if t.get('id') == 'VT':
                continue
            tot = t.find('totals')
            if tot is None:
                continue
            fu, pa = tot.find('fumbles'), tot.find('pass')
            out[os.path.basename(f)[:-4]] = (
                int(pa.get('int', 0) or 0) if pa is not None else 0,
                int(fu.get('lost', 0) or 0) if fu is not None else 0)
            break
    return out


def wmt_counts():
    out = {}
    for f in glob.glob(os.path.join(HERE, 'hokiesports/raw_wmt/*.json')):
        comps = json.load(open(f))['data']['competitors']
        for c in comps:
            if (c.get('nameTabular') or c.get('name')) == 'Virginia Tech':
                continue
            st = {}
            for ts in c['teamStats']:
                st.update(ts.get('statistic', {}))
            out[os.path.basename(f)[:-5]] = (int(st.get('sPassInterceptions') or 0),
                                             int(st.get('sFumblesLost') or 0))
    return out


def main():
    G = pd.read_parquet(f'{D}/unified/games.parquet')
    pbp, kick = pbp_counts()
    box, wmt = box_counts(), wmt_counts()
    espn = {}
    for f in glob.glob(f'{D}/espn/box/*.parquet'):
        e = pd.read_parquet(f)
        e = e[(e.oppId == 259) & e.intThrown.notna() & e.fumblesLost.notna()]
        for r in e.itertuples():
            espn[r.date] = (int(r.intThrown), int(r.fumblesLost))

    def one(r):
        hs = str(r.hsGameId) if pd.notna(r.hsGameId) else None
        if hs in box:
            return (*box[hs], 'box')
        if hs in wmt:
            return (*wmt[hs], 'wmt')
        # ESPN dates are UTC, so night games can land on the next day.
        d0 = pd.Timestamp(str(r.date)[:10])
        for d in (d0, d0 + pd.Timedelta(days=1)):
            if d.strftime('%Y-%m-%d') in espn:
                return (*espn[d.strftime('%Y-%m-%d')], 'espn')
        if r.season == 2002 and r.opponent == 'West Virginia':
            return (1, 0, 'teamstats')  # box 5988: WVU 13-20-1 passing, fumbles 2-0
        i, fm = pbp.loc[r.gameKey] if r.gameKey in pbp.index else (0, 0)
        cf = str(r.cfbdGameId) if pd.notna(r.cfbdGameId) else None
        return (int(i), int(fm) + kick.get(cf, 0), 'pbp')

    v = G.apply(one, axis=1)
    G['interceptions'], G['fumblesRecovered'], G['source'] = v.str[0], v.str[1], v.str[2]
    G['takeaways'] = G.interceptions + G.fumblesRecovered
    games = G[['season', 'date', 'opponent', 'interceptions', 'fumblesRecovered', 'takeaways',
               'source']].sort_values('date')
    s = games.groupby('season').agg(games=('takeaways', 'size'),
                                    interceptions=('interceptions', 'sum'),
                                    fumblesRecovered=('fumblesRecovered', 'sum'),
                                    takeaways=('takeaways', 'sum')).reset_index()
    s['takeawaysPerGame'] = (s.takeaways / s.games).round(2)
    os.makedirs(f'{D}/derived', exist_ok=True)
    games.to_csv(f'{D}/derived/vt_takeaways_by_game.csv', index=False)
    s.to_csv(f'{D}/derived/vt_takeaways_by_season.csv', index=False)
    print(s.to_string(index=False))


if __name__ == '__main__':
    main()
