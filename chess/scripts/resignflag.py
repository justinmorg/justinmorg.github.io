#!/usr/bin/env python3
"""
resignflag.py — resignations and flags as errors (exploratory, 2026-10-24).

Usage:
    python3 chess/scripts/resignflag.py OUTDIR \
        2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn Q4-2025=q4.pgn \
        2026=corpus.pgn CC-2024Q4=cc_2024q4_analyzed.pgn CC-2026=cc_2026febapr_analyzed.pgn \
        --panel chess/data/panel

Labels starting `CC-` are chess.com (player `justinmorg`); everything else is
Lichess `jamorgan`. Scope is 180+2 and 300+0 only (the outcomes.py scope; 5,636
games for the eight blocks above). Panel = the 40 thread-9 pairs (pairs 7, 15,
35, 40 dropped, as in the test), both months, read from `<panel>/ann/`.

No replay — ends of games come from headers plus the last SAN, so it runs in
seconds. Gate (printed): seven-block subset 5,404 games, 2,619 W / 2,585 L,
flag wins 434, flag losses 150.

Loss kinds, per (game, side):
  mate    last SAN ends '#'
  flag    'Time forfeit' / '... won on time' AND loser's last [%clk] < 30s
  left    the same termination with >= 30s on the loser's clock (Lichess writes
          'Time forfeit' when a player leaves and the opponent claims), plus
          chess.com 'won - game abandoned'
  resign  Lichess 'Normal' decisive non-mate / chess.com 'won by resignation'

Counterfactual ("expected points forfeited"): the final score of players who
were in the same state and played on — eval band (player POV) x own/opp clock
ratio band x game-length band x time control, from every game in scope (him,
his opponents, panel, panel opponents), positions from ply 20 sampled every
other ply-pair with >= 6 more plies played. Fallback to a clock-free cell if a
cell has < 30 positions. For a flag the clock axis is set to 'even': what that
board scores when the clock is not the problem — an upper bound on the clock's
cost. Selection caveat: players who chose to play on may have had reasons.
"""
import csv
import glob
import gzip
import os
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd

TOK = re.compile(r'([NBRQKa-hO][^\s{}]*?)\s*\{\s*\[%eval ([^\]]+)\]\s*'
                 r'\[%clk (\d+):(\d+):(\d+(?:\.\d+)?)\]\s*\}')
HDR = re.compile(r'^\[(\w+) "(.*)"\]$')
TCS = {"180+2", "300+0"}
BAD_PAIRS = {7, 15, 35, 40}
LEFT_CLOCK = 30.0
ORDER = ['me', 'my_opp', 'improver', 'control', 'panel_opp']

EB = [-10 ** 6, -1500, -1000, -700, -500, -400, -300, -200, -100, 100, 300, 10 ** 6]
EL = ['<-15', '-15..-10', '-10..-7', '-7..-5', '-5..-4', '-4..-3', '-3..-2', '-2..-1',
      'level', '+1..+3', '>+3']
CB = [0, 0.5, 0.8, 1.25, 2.0, 1e9]
CL = ['clk<0.5x', '0.5-0.8x', 'even', '1.25-2x', '>2x']
PB = [0, 40, 80, 10 ** 6]
PL = ['<20 moves', '20-40', '40+']


def ev(s):
    s = s.strip()
    if s.startswith('#'):
        n = int(s[1:])
        if n == 0:
            return None
        return (10000 - 10 * abs(n)) * (1 if n > 0 else -1)
    return int(round(float(s) * 100))


def read_games(path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt', errors='replace') as f:
        h, body = {}, []
        for line in f:
            line = line.rstrip('\n')
            m = HDR.match(line)
            if m:
                if body:
                    yield h, ' '.join(body)
                    h, body = {}, []
                h[m.group(1)] = m.group(2)
            elif line.strip():
                body.append(line)
        if h:
            yield h, ' '.join(body)


def parse(h, body):
    sans, evs, clks = [], [], []
    for m in TOK.finditer(body):
        sans.append(m.group(1))
        evs.append(ev(m.group(2)))
        clks.append(int(m.group(3)) * 3600 + int(m.group(4)) * 60 + float(m.group(5)))
    return sans, evs, clks


def load(blocks, panel):
    rows = []
    for label, path in blocks:
        cc = label.upper().startswith('CC-')
        user = 'justinmorg' if cc else 'jamorgan'
        for h, body in read_games(path):
            if h.get('TimeControl') not in TCS:
                continue
            sans, evs, clks = parse(h, body)
            rows.append(dict(src='me', block=label, site='cc' if cc else 'li',
                             gid=h.get('GameId') or h.get('Link'), white=h['White'],
                             black=h['Black'], me=user, pair=-1, pid=None,
                             tc=h['TimeControl'], result=h['Result'],
                             term=h.get('Termination', ''), sans=sans, evs=evs, clks=clks))
    grp = {}
    with open(os.path.join(panel, 'panel_ranks.csv')) as f:
        for r in csv.DictReader(f):
            grp[r['id']] = (r['group'], int(r['pair']))
    for p in sorted(glob.glob(os.path.join(panel, 'ann', '*_analyzed.pgn.gz'))):
        pid, month = os.path.basename(p).split('_')[:2]
        g, pair = grp.get(pid, ('?', -1))
        if pair in BAD_PAIRS:
            continue
        for h, body in read_games(p):
            if h.get('TimeControl') not in TCS:
                continue
            sans, evs, clks = parse(h, body)
            rows.append(dict(src='panel', block=month, site='li', gid=h.get('GameId'),
                             white=h['White'], black=h['Black'], me=pid, pair=pair, pid=pid,
                             group=g, tc=h['TimeControl'], result=h['Result'],
                             term=h.get('Termination', ''), sans=sans, evs=evs, clks=clks))
    return rows


def side_table(rows):
    out = []
    for g in rows:
        n = len(g['sans'])
        term = g['term'].lower()
        mated = n > 0 and g['sans'][-1].endswith('#')
        base = int(g['tc'].split('+')[0])
        fe = next((e for e in reversed(g['evs']) if e is not None), None)
        for side in ('w', 'b'):
            name = g['white'] if side == 'w' else g['black']
            if g['src'] == 'me':
                who = 'me' if name.lower() == g['me'].lower() else 'my_opp'
            else:
                who = g['group'] if name == g['pid'] else 'panel_opp'
            sgn = 1 if side == 'w' else -1
            res = g['result']
            score = 0.5 if res not in ('1-0', '0-1') else \
                float((res == '1-0') == (side == 'w'))
            if score == 0.5:
                how = 'draw'
            elif mated:
                how = 'mate'
            elif term == 'time forfeit' or 'won on time' in term:
                how = 'timeforfeit'
            elif 'abandon' in term:
                how = 'abandon'
            elif term == 'normal' or 'resignation' in term:
                how = 'resign'
            else:
                how = 'other:' + term
            f = (10000 if score == 1 else -10000) if mated else fe
            par = 0 if side == 'w' else 1
            own = [c for i, c in enumerate(g['clks']) if i % 2 == par]
            opp = [c for i, c in enumerate(g['clks']) if i % 2 != par]
            out.append(dict(src=g['src'], block=g['block'], site=g['site'], gid=g['gid'],
                            side=side, who=who, pair=g['pair'], pid=g['pid'], tc=g['tc'],
                            score=score, how=how, plies=n,
                            fe_pov=None if f is None else f * sgn,
                            own_clk=own[-1] if own else base, opp_clk=opp[-1] if opp else base))
    return pd.DataFrame(out)


def benchmark(rows):
    recs = []
    for g in rows:
        n = len(g['sans'])
        res = g['result']
        sw = 1.0 if res == '1-0' else 0.0 if res == '0-1' else 0.5
        base = int(g['tc'].split('+')[0])
        cw = cb = base
        for i in range(n - 6):
            if i % 2 == 0:
                cw = g['clks'][i]
            else:
                cb = g['clks'][i]
            e = g['evs'][i]
            if e is None or i < 20 or i % 4 not in (0, 1):
                continue
            side = 'b' if i % 2 == 0 else 'w'          # side to move decides to play on
            pov = e if side == 'w' else -e
            own, opp = (cw, cb) if side == 'w' else (cb, cw)
            recs.append((g['tc'], i, pov, own / max(opp, 1.0), sw if side == 'w' else 1 - sw))
    P = pd.DataFrame(recs, columns=['tc', 'ply', 'pov', 'ratio', 'score'])
    P['eb'] = pd.cut(P.pov, EB, labels=EL)
    P['cb'] = pd.cut(P.ratio, CB, labels=CL)
    P['pb'] = pd.cut(P.ply, PB, labels=PL)
    return P


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    out = argv[1]
    panel = None
    blocks = []
    it = iter(argv[2:])
    for a in it:
        if a == '--panel':
            panel = next(it)
        else:
            lab, path = a.split('=', 1)
            blocks.append((lab, path))
    if not panel:
        sys.exit('--panel is required')
    os.makedirs(out, exist_ok=True)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_columns', 30)
    rng = np.random.default_rng(23)

    rows = load(blocks, panel)
    d = side_table(rows)

    # ---- gate ----
    me = d[d.who == 'me']
    s7 = me[me.block != 'Q4-2025']
    gate = (len(s7), int((s7.score == 1).sum()), int((s7.score == 0).sum()),
            int(((s7.how == 'timeforfeit') & (s7.score == 1)).sum()),
            int(((s7.how == 'timeforfeit') & (s7.score == 0)).sum()))
    print('gate (7-block games, W, L, flag wins, flag losses):', gate,
          'OK' if gate == (5404, 2619, 2585, 434, 150) else 'MISMATCH vs 5404/2619/2585/434/150')
    print('scope:', d.groupby('who').size().to_dict())

    # ---- benchmark ----
    P = benchmark(rows)
    E = P.groupby(['tc', 'eb', 'cb', 'pb'], observed=True).score.agg(['mean', 'size'])
    E2 = P.groupby(['tc', 'eb', 'pb'], observed=True).score.agg(['mean', 'size'])
    E3 = P.groupby(['tc', 'eb'], observed=True).score.mean()
    print(f'\nbenchmark positions {len(P):,}')
    print('Play-on score by eval band x clock ratio (3+2):')
    print(P[P.tc == '180+2'].groupby(['eb', 'cb'], observed=True).score.mean().unstack().round(2))

    def expect(tc, eb, cb, pb):
        if pd.isna(eb):
            return np.nan
        for tab, k in ((E, (tc, eb, cb, pb)), (E2, (tc, eb, pb))):
            if k in tab.index and tab.loc[k, 'size'] >= 30:
                return tab.loc[k, 'mean']
        return E3.loc[(tc, eb)]

    # ---- losses ----
    L = d[d.score == 0].copy()
    L['kind'] = L.how
    tf = L.how == 'timeforfeit'
    L.loc[tf & (L.own_clk < LEFT_CLOCK), 'kind'] = 'flag'
    L.loc[tf & (L.own_clk >= LEFT_CLOCK), 'kind'] = 'left'
    L.loc[L.how == 'abandon', 'kind'] = 'left'
    L['eb'] = pd.cut(L.fe_pov.astype(float), EB, labels=EL)
    L['cb'] = pd.cut(L.own_clk / L.opp_clk.clip(lower=1), CB, labels=CL)
    L['pb'] = pd.cut(L.plies, PB, labels=PL)
    L['xs'] = [expect(r.tc, r.eb, 'even' if r.kind == 'flag' else r.cb, r.pb)
               for r in L.itertuples()]
    G = d.groupby('who').size()

    print('\n=== Loss composition, % of games ===')
    print((L.groupby(['who', 'kind']).size().unstack(fill_value=0).div(G, axis=0) * 100)
          .loc[ORDER].round(2))

    R = L[L.kind == 'resign']
    fe = R.fe_pov.astype(float)
    print('\n=== Resignations: board at resignation (player POV) ===')
    print(pd.DataFrame({
        'n': R.groupby('who').size(),
        'median cp': R.groupby('who').fe_pov.median(),
        '% better than -5': R[fe > -500].groupby('who').size() / R.groupby('who').size() * 100,
        'per100 >+1': R[fe > 100].groupby('who').size() / G * 100,
        'per100 level': R[(fe > -100) & (fe <= 100)].groupby('who').size() / G * 100,
        'per100 -3..-1': R[(fe > -300) & (fe <= -100)].groupby('who').size() / G * 100,
        'per100 -5..-3': R[(fe > -500) & (fe <= -300)].groupby('who').size() / G * 100,
    }).loc[ORDER].round(2))

    F = L[L.kind == 'flag']
    fb = pd.cut(F.fe_pov.astype(float), [-1e9, -300, -100, 100, 300, 1e9],
                labels=['lost <-3', '-3..-1', 'level', '+1..+3', 'winning >+3'])
    print('\n=== Flags (<30s): board at the flag, per 100 games ===')
    print((F.groupby(['who', fb], observed=False).size().unstack(fill_value=0)
           .div(G, axis=0) * 100).loc[ORDER].round(2))

    # ---- per (game, side) metrics, per 100 games ----
    f = L.fe_pov.astype(float)
    x = L['xs']
    met = pd.DataFrame({
        'gid': L.gid, 'side': L.side, 'who': L.who,
        'resign_pts': np.where(L.kind == 'resign', x, 0),
        'resign_early_pts': np.where((L.kind == 'resign') & (f > -500), x, 0),
        'resign_early_n': ((L.kind == 'resign') & (f > -500)).astype(float),
        'left_pts': np.where(L.kind == 'left', x, 0),
        'flag_n': (L.kind == 'flag').astype(float),
        'flag_good_n': ((L.kind == 'flag') & (f > -100)).astype(float),
        'flag_pts': np.where(L.kind == 'flag', x, 0),
    })
    M = [c for c in met.columns if c not in ('gid', 'side', 'who')]
    dm = d.merge(met, on=['gid', 'side', 'who'], how='left').fillna({m: 0 for m in M})
    for m in M:
        dm[m] *= 100
    print('\n=== Per 100 games, by group ===')
    print(dm.groupby('who')[M].mean().loc[ORDER].round(2))

    B = 4000
    mine = dm[dm.who == 'me'].set_index('gid').sort_index()
    theirs = dm[dm.who == 'my_opp'].set_index('gid').sort_index()
    assert (mine.index == theirs.index).all()
    print('\n=== Me minus my opponents (same games, game bootstrap) ===')
    for m in M:
        diff = (mine[m] - theirs[m]).values
        bs = diff[rng.integers(0, len(diff), (B, len(diff)))].mean(1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print(f'{m:18s} {diff.mean():+6.2f} [{lo:+.2f}, {hi:+.2f}]')

    pan = dm[dm.who.isin(['improver', 'control'])]
    print('\n=== Me minus panel group (panel players and my games resampled) ===')
    mev = mine[M].values
    for grp in ['improver', 'control']:
        units = [g[M].values for _, g in pan[pan.who == grp].groupby('pid')]
        est = mev.mean(0) - np.concatenate(units).mean(0)
        bs = []
        for _ in range(1500):
            pick = rng.integers(0, len(units), len(units))
            arr = np.concatenate([units[i] for i in pick])
            bs.append(mev[rng.integers(0, len(mev), len(mev))].mean(0) - arr.mean(0))
        lo, hi = np.percentile(np.array(bs), [2.5, 97.5], axis=0)
        for j, m in enumerate(M):
            print(f'{grp:9s} {m:18s} {est[j]:+6.2f} [{lo[j]:+.2f}, {hi[j]:+.2f}]')

    print('\n=== Panel by month ===')
    print(pan.groupby(['who', 'block'])[M].mean().round(2).T)
    pm = pan.groupby(['pair', 'who', 'block'])[M].mean()
    pairs = sorted(pan.pair.unique())
    print('\n=== Improver change minus control change, pair bootstrap ===')
    for m in M:
        ch = lambda p, g: pm.loc[(p, g, '2609'), m] - pm.loc[(p, g, '2509'), m]  # noqa: E731
        dd = np.array([ch(p, 'improver') - ch(p, 'control') for p in pairs])
        bs = dd[rng.integers(0, len(dd), (B, len(dd)))].mean(1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        p2 = 2 * min((bs <= 0).mean(), (bs >= 0).mean())
        print(f'{m:18s} {dd.mean():+6.2f} [{lo:+.2f}, {hi:+.2f}]  p~{p2:.2f}')

    print('\n=== Me, Lichess blocks, by era and time control ===')
    li = dm[(dm.src == 'me') & (dm.site == 'li')].copy()
    li['era'] = np.where(li.block.str.contains('2026'), '2026', '2024H2-2025')
    for who in ['me', 'my_opp']:
        for (tc, era), g in li[li.who == who].groupby(['tc', 'era']):
            if len(g) < 100:
                continue
            v = g[['flag_n', 'flag_good_n', 'flag_pts']].values
            bs = np.array([v[rng.integers(0, len(v), len(v))].mean(0) for _ in range(2000)])
            lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
            print(who, tc, era, len(g), ' '.join(
                f'{k}={a:.2f}[{l:.2f},{h:.2f}]' for k, a, l, h in
                zip(['flags', 'flags_level+', 'pts'], v.mean(0), lo, hi)))

    L.drop(columns=['eb', 'cb', 'pb']).to_csv(os.path.join(out, 'losses.csv'), index=False)
    dm.to_csv(os.path.join(out, 'per_side.csv.gz'), index=False)
    print(f'\nwrote {out}/losses.csv, {out}/per_side.csv.gz')


if __name__ == '__main__':
    main(sys.argv)
