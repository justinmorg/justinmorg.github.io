import sys, numpy as np, pandas as pd
sys.argv=['x','/home/claude/features7']
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('/home/claude/justinmorg.github.io/chess/scripts/clockmodel.py').read().split("print('\\nexpected score")[0])
f=fits[True]
def E(wpv, my, op):
    d=pd.DataFrame({'my':np.asarray(my,float),'op':np.asarray(op,float),'L':np.log(np.clip(wpv,.02,.98)/(1-np.clip(wpv,.02,.98)))})
    return np.asarray(f.predict(X(d)))
t=m[m.block=='TREAT'].copy()
myb=t.my.values; mya=t.clk.values; op=t.op.values
t['clock_cost']=E(t.wp_before,myb,op)-E(t.wp_before,mya,op)     # board held fixed
t['board_cost']=E(t.wp_before,mya,op)-E(t.wp_after,mya,op)
c=pd.read_csv('/home/claude/lt/classified.csv')
print('F block 3+2, moves 15+: per game, expected score spent on clock %.1f pts, on board %.1f pts' % (t.groupby('gid').clock_cost.sum().mean()*100, t.groupby('gid').board_cost.sum().mean()*100))
lt=t[t.spend>=15]; print('long thinks (>=15s): n=%d, avg clock cost %.1f pts, avg board cost %.1f pts' % (len(lt), lt.clock_cost.mean()*100, lt.board_cost.mean()*100))
print('quick (<=5s): avg clock cost %.2f pts, board cost %.1f pts' % (t[t.spend<=5].clock_cost.mean()*100, t[t.spend<=5].board_cost.mean()*100))
# join categories for long thinks in F block
key=lambda d: d.gid+':'+d.ply.astype(str)
pos=pd.read_json('/home/claude/lt/positions.jsonl',lines=True); pos['k']=key(pos)
c['k']=pos[['k']].iloc[:0].k if False else None
c=pd.read_csv('/home/claude/lt/classified.csv')
j=t.merge(c[['gid','ply','cat','ngood','good','san']],on=['gid','ply'])
j=j[j.spend>=15]
print('\nF-block long thinks by category: avg clock cost / board cost (pts), n')
print(j.groupby('cat').agg(n=('cat','size'),clock=('clock_cost','mean'),board=('board_cost','mean')).mul([1,100,100]).round(1).to_string())
w=j[(j.cat=='4+ fine moves')&(j.good)].sort_values('clock_cost',ascending=False).head(4)
for r in w.itertuples():
    print(f"https://lichess.org/{r.gid}#{r.ply}  move {r.fullmove} {r.san}: spent {r.spend:.0f}s with {r.my:.0f}s left vs {r.op:.0f}s, engine {r.wp_before*100:.0f}% -> clock cost {r.clock_cost*100:.1f} pts, board cost {r.board_cost*100:+.1f}")
