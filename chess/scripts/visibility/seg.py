import numpy as np, pandas as pd
m = pd.read_parquet('moves.parquet')
m = m[m.fullmove >= 6].copy()
def matb(x):
    if x <= -3: return '1 down piece+'
    if x <= -1: return '2 down 1-2 pawns'
    if x == 0: return '3 even'
    if x <= 2: return '4 up 1-2 pawns'
    return '5 up piece+'
m['mat'] = m.pmat.map(matb)
d = m.my - m.op
m['clock'] = np.select([m.my < 20, d <= -30, d >= 30], ['0 me <20s', '1 me behind 30s+', '3 me ahead 30s+'], '2 clocks within 30s')
m['queens'] = np.where(m.queens_on == 1, 'queens on', 'queens off')
m['phase'] = np.select([m.fullmove <= 12, m.npm_light > 14], ['1 opening (<=12)', '2 middlegame'], '3 endgame')
m['err'] = m.cost >= .10
m['ecost'] = np.where(m.err, m.cost, 0)
lost = m.score == 0
print('games', m.gid.nunique(), 'lost', m[lost].gid.nunique(), 'errors', m.err.sum(), 'in lost games', m[lost].err.sum())
print('total error cost in lost games, pts:', round(m[lost].ecost.sum()*100))
def tab(col, sub=lost):
    s = m[sub]
    t = s.groupby(col).agg(moves=('err','size'), errors=('err','sum'), cost=('ecost','sum'))
    t['share_moves%'] = 100*t.moves/t.moves.sum()
    t['share_loss_cost%'] = 100*t.cost/t.cost.sum()
    t['err_per_100'] = 100*t.errors/t.moves
    t['avg_err_size'] = 100*t.cost/t.errors
    t['ratio'] = t['share_loss_cost%']/t['share_moves%']
    return t.drop(columns='cost').round(1)
for c in ('mat','clock','queens','phase'):
    print('\n== LOST GAMES by', c); print(tab(c).to_string())
    print('-- ALL GAMES err/100 by', c); print(tab(c, m.score>-1)[['share_moves%','share_loss_cost%','err_per_100','avg_err_size']].to_string())
m.to_parquet('seg.parquet')
