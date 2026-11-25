#!/usr/bin/env python3
"""Clock-value model, 3+2 (exploratory, 2026-11-25).

Expected final score from the engine win probability and both clocks, fitted
on every own move from move 15 on. Fractional logit (GLM binomial), features
logit(wp), log(my_clk+5), log(opp_clk+5) and the two eval x clock
interactions; each game weighted once; SEs clustered by game. Fitted on the
six settled blocks, validated on the F treatment block (held out).

Predictive, not causal: low clock at a given eval also marks a game that has
been hard for you, so clock "costs" here likely overstate the true cost.

  python3 chess/scripts/clockmodel.py /home/claude/features7
(features.py output that includes a TREAT block.)
"""
import sys
import numpy as np, pandas as pd, statsmodels.api as sm
FEAT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/features7'
m = pd.read_csv(FEAT+'/moves.csv.gz', low_memory=False)
g = pd.read_csv(FEAT+'/games.csv').set_index('gid')
m = m[(m.tc == '180+2') & (m.fullmove >= 15) & m.clk.notna() & m.opp_clk.notna() & m.spend.notna()].copy()
m['score'] = m.gid.map(g.score)
m['my'] = (m.clk + m.spend - 2).clip(lower=0)          # my clock before this move
m['op'] = m.opp_clk.clip(lower=0)
m['L'] = np.log(m.wp_before.clip(.02,.98)/(1-m.wp_before.clip(.02,.98)))
def X(d, clock=True):
    a = np.log(d.my+5); b = np.log(d.op+5)
    cols = {'L': d.L}
    if clock: cols.update({'a': a, 'b': b, 'La': d.L*a, 'Lb': d.L*b})
    return sm.add_constant(pd.DataFrame(cols), has_constant='add')
m['w'] = 1/m.groupby('gid').gid.transform('size')     # each game counts once
tr, te = m[m.block != 'TREAT'], m[m.block == 'TREAT']
fits = {}
for k in (False, True):
    fits[k] = sm.GLM(tr.score, X(tr,k), family=sm.families.Binomial(), freq_weights=tr.w*len(tr.gid.unique())/tr.w.sum()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(tr.gid)[0]})
    p = fits[k].predict(X(te,k)); br = np.average((te.score-p)**2, weights=te.w)
    print('clock' if k else 'eval-only', 'held-out Brier on F block = %.4f' % br)
print(fits[True].summary().tables[1])
print('games', tr.gid.nunique(), 'train /', te.gid.nunique(), 'test; snapshots', len(tr), len(te))
f = fits[True]
def P(wp, my, op):
    d = pd.DataFrame({'my':[my], 'op':[op], 'L':[np.log(wp/(1-wp))]}); return float(f.predict(X(d))[0])
print('\nexpected score (3+2, move 15+)   rows: engine win% | cols: my clock (opp 60s / opp 150s)')
clocks = [5,10,20,45,90,150]
print('eval  ' + ''.join(f'{c:>6}s' for c in clocks))
for wp in (.5,.65,.8,.9):
    print(f'{int(wp*100):3d}%  ' + ''.join(f'{P(wp,c,60)*100:6.0f}%' for c in clocks) + '   | opp 150s: ' + ' '.join(f'{P(wp,c,150)*100:.0f}' for c in clocks))
print('\ncost of a 30s think (clock X -> X-28), opp 60s, in points of expected score:')
for wp in (.5,.65,.8):
    print(f'{int(wp*100)}%: ' + '  '.join(f'{X0}s:{(P(wp,X0,60)-P(wp,max(X0-28,1),60))*100:+.1f}' for X0 in (40,60,90,150)))
print('\nexample 80%% eval, me 10s vs opp 150s: %.0f%%;  same eval, clocks level 60/60: %.0f%%' % (P(.8,10,150)*100, P(.8,60,60)*100))
# calibration check of eval-only: what does the engine "80%" actually score?
print('sanity, level eval & equal clocks: 20/20 %.0f%%  60/60 %.0f%%  150/150 %.0f%%' % tuple(P(.5,c,c)*100 for c in (20,60,150)))
e = tr[(tr.wp_before.between(.75,.85))]; print('engine 75-85%% bucket actual score (weighted) %.1f%%' % (np.average(e.score, weights=e.w)*100))
from scipy.optimize import brentq
print('\nbreak-even: engine win% the move must reach after a 30s think (opp 60s)')
for wp in (.5,.65,.8):
    row=[]
    for X0 in (60,90,150):
        tgt=P(wp,X0,60)
        try: need=brentq(lambda w: P(w,X0-28,60)-tgt, .03,.97); row.append(f'{X0}s: {wp*100:.0f}%->{need*100:.0f}%')
        except ValueError: row.append(f'{X0}s: unreachable')
    print('  '.join(row))
