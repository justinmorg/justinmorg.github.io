import pandas as pd, numpy as np, chess, sys
sys.path.insert(0,'/home/claude/repo/chess/scripts'); from hanging import see
from emodel import E
m=pd.read_parquet('seg.parquet').sort_values(['gid','ply'])
print('model check, mean |E diff|', np.abs(E(m.wp_before,m.clk,m.op)-m.E_before).mean())
fen=pd.read_csv('/home/claude/feat/fens.csv.gz',dtype={'gid':str,'block':str})
m=m.merge(fen[['gid','ply','fen']],on=['gid','ply'])
m['prev_wp_after']=m.groupby('gid').wp_after.shift(); m['prev_ply']=m.groupby('gid').ply.shift()
m=m[(m.prev_ply==m.ply-2)&(m.fullmove>=8)&(m.mate_flag==0)].copy()
m['gift']=E(m.wp_before,m.my,m.op)-E(m.prev_wp_after,m.my,m.op)   # what the opponent's last move handed me
def bestcap(f):
    b=chess.Board(f); return max([see(b,mv) for mv in b.legal_moves if b.is_capture(mv)]+[0])
g=m[m.gift>=.10].copy()
g['grab']=[bestcap(f) for f in g.fen]
g['visible']=np.where(g.grab>=200,'material to grab (SEE>=2)','nothing to grab')
g['gb']=pd.cut(g.gift,[.10,.20,.35,1],labels=['gift 10-20','gift 20-35','gift 35+'])
g['gave_back']=g.cost>=.10
print('opponent mistakes (gift>=10 pts):',len(g))
t=g.groupby(['gb','visible'],observed=True).agg(n=('cost','size'),gave_back=('gave_back','mean'),avg_cost=('cost','mean'),spend=('spend','median'),wp=('wp_before','median'))
print(t.round(3).to_string())
# baseline: my error rate at similar engine win% when there was no opponent gift
base=m[(m.gift.abs()<.03)]
for lo,hi in [(.4,.6),(.6,.8),(.8,.95)]:
    print(f'baseline err rate, no gift, wp {lo}-{hi}: {(base[base.wp_before.between(lo,hi)].cost>=.10).mean():.3f}',
          f'| after gift, nothing to grab: {(g[(g.visible=="nothing to grab")&g.wp_before.between(lo,hi)].cost>=.10).mean():.3f}',
          f'| after gift, material to grab: {(g[(g.visible!="nothing to grab")&g.wp_before.between(lo,hi)].cost>=.10).mean():.3f}')
g.drop(columns=['fen']).to_parquet('oppgifts.parquet'); m.drop(columns=['fen']).to_parquet('withgift.parquet')
