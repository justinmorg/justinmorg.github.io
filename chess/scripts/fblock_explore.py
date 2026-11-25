#!/usr/bin/env python3
"""Exploratory, NOT pre-registered: 11 metrics fixed before running, treatment
block vs the six settled blocks pooled, game-level label permutation (5,000,
seed 23, two-sided). Bonferroni bar p < 0.005. Reads features.py output for
the seven blocks at /home/claude/features7/."""
import numpy as np, pandas as pd
g = pd.read_csv('/home/claude/features7/games.csv')
m = pd.read_csv('/home/claude/features7/moves.csv.gz', low_memory=False)
m = m[(m.mate_flag == 0)]
T = g.block.eq('TREAT')
# per-game numerators/denominators for each metric
G = g.set_index('gid')
exp = 1/(1+10**((G.opp_elo-G.my_elo)/400))
lost = G.score.eq(0); won = G.score.eq(1)
per = {}
per['G1 score minus Elo-expected'] = (G.score-exp, pd.Series(1.0,index=G.index))
per['G2 lost on time (per game)'] = ((lost & G.is_flag.eq(1)).astype(float), pd.Series(1.0,index=G.index))
per['G3 won on time (per game)'] = ((won & G.is_flag.eq(1)).astype(float), pd.Series(1.0,index=G.index))
per['G4 reached a winning position'] = (G.bucket.eq('reached').astype(float), pd.Series(1.0,index=G.index))
pk = G.peak >= 300
per['G5 score when ever +3 or better'] = (G.score.where(pk,0.0), pk.astype(float))
lv = G.eg_entry_cp.between(-100,100)
per['G6 score in level endgames'] = (G.score.where(lv,0.0), lv.astype(float))
mm = m[m.fullmove > 12].copy(); mm['bl'] = (mm.drop_cp >= 200).astype(float)
def agg(mask, val='bl'):
    s = mm[mask].groupby('gid')[val].agg(['sum','count']).reindex(G.index, fill_value=0)
    return s['sum'].astype(float), s['count'].astype(float)
per['M1 blunder rate, moves 13+'] = agg(mm.fullmove > 12)
per['M2 blunder rate, level positions (±1)'] = agg(mm.cp_before.abs() <= 100)
per['M3 blunder rate, move 26+, not lost'] = agg((mm.fullmove >= 26) & (mm.cp_before > -300))
m32 = m[(m.tc == '180+2') & m.spend.notna()]
s = m32[m32.fullmove <= 25].groupby('gid').spend.agg(['sum','count']).reindex(G.index, fill_value=0)
per['C1 avg seconds/move, moves 1-25 (3+2)'] = (s['sum'].astype(float), s['count'].astype(float))
m32 = m32.assign(tt=(m32.clk <= 15).astype(float))
s = m32.groupby('gid').tt.agg(['sum','count']).reindex(G.index, fill_value=0)
per['C2 share of moves with ≤15s left (3+2)'] = (s['sum'].astype(float), s['count'].astype(float))
lab = T.values; rng = np.random.default_rng(23); N = 5000
rows = []
for k,(num,den) in per.items():
    num = num.values; den = den.values
    def diff(l):
        a = num[l].sum()/den[l].sum(); b = num[~l].sum()/den[~l].sum(); return a, b
    a,b = diff(lab); obs = a-b
    perm = np.empty(N)
    for i in range(N):
        l = rng.permutation(lab); x,y = diff(l); perm[i] = x-y
    p = (np.sum(np.abs(perm) >= abs(obs))+1)/(N+1)
    y26 = g.block.eq('Y2026').values; c = num[y26].sum()/den[y26].sum()
    rows.append((k, a, b, c, obs, p, int(den[lab].sum())))
pct = lambda k: not k.startswith('C1')
for k,a,b,c,o,p,n in rows:
    f = (lambda v: f'{v*100:6.2f}%') if pct(k) else (lambda v: f'{v:6.2f}s')
    fd = (f'{o*100:+.2f} pp') if pct(k) else f'{o:+.2f}s'
    if k.startswith('G1'): f=lambda v: f'{v*100:+6.2f}'; fd=f'{o*100:+.2f}'
    print(f'{k:42s} T {f(a)}  base {f(b)}  2026 {f(c)}  diff {fd:>10s}  p={p:.4f}  nT={n}')
print('elo mean T %.0f  2026 %.0f  base %.0f' % (G.my_elo[T.values].mean(), G.my_elo[g.block.eq("Y2026").values].mean(), G.my_elo[~T.values].mean()))
print('tc mix T', g[T].tc.value_counts().to_dict(), ' 2026', g[g.block.eq("Y2026")].tc.value_counts().to_dict())
