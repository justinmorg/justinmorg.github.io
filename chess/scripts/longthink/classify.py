import json, math, pandas as pd, numpy as np
wp=lambda cp: 1/(1+math.exp(-0.00368208*max(min(cp,3000),-3000)))
pos={f"{r['gid']}:{r['ply']}":r for r in map(json.loads,open('/home/claude/lt/positions.jsonl'))}
rows=[]
for f in ('mpv_0.jsonl','mpv_1.jsonl'):
    for l in open('/home/claude/lt/'+f):
        e=json.loads(l); r=pos[e['k']]
        mv=e['mv']; ev={u:wp(s) for u,s in mv}
        top=sorted(ev.values(),reverse=True); best=top[0]
        ngood=sum(1 for v in top if v>=best-0.05)
        gap2=best-top[1] if len(top)>1 else 1.0
        played=ev[r['played']]
        if best<0.20: cat='already lost (<20%)'
        elif best>0.85 and ngood>=2: cat='winning, several moves keep it'
        elif ngood==1 and gap2>=0.10: cat='only move (puzzle)'
        elif ngood<=3: cat='2-3 good moves'
        else: cat='4+ fine moves'
        rows.append(dict(gid=r['gid'],ply=r['ply'],san=r['san'],kind=r['kind'],spend=r['spend'],fullmove=r['fullmove'],cat=cat,ngood=ngood,best=best,loss=best-played,good=played>=best-0.05,early=r['fullmove']<=15,clk=r['clk']))
d=pd.DataFrame(rows)
order=['only move (puzzle)','2-3 good moves','4+ fine moves','winning, several moves keep it','already lost (<20%)']
def tab(sub,label):
    t=sub.groupby('cat').agg(n=('cat','size'),found_good=('good','mean'),avg_loss=('loss','mean')).reindex(order)
    t['share']=t.n/len(sub); print(f'\n{label} (n={len(sub)})'); print((t[['share','n','found_good','avg_loss']]).round(3).to_string())
L=d[d.kind=='long']; Q=d[d.kind=='quick']
tab(L,'LONG thinks >=15s'); tab(Q,'QUICK moves <=5s, move 8+')
tab(L[L.spend>=30],'VERY long >=30s')
print('\nlong thinks by phase:'); print(pd.crosstab(L.early.map({True:'moves <=15',False:'move 16+'}),L.cat,normalize='index').reindex(columns=order).round(3).to_string())
print('\nlong thinks at move<=15 with 4+ fine moves: %d of %d long thinks (%.1f%%), mean spend %.1fs, clock left %.0fs' % (((L.early)&(L.cat=='4+ fine moves')).sum(), len(L), ((L.early)&(L.cat=='4+ fine moves')).mean()*100, L[(L.early)&(L.cat=='4+ fine moves')].spend.mean(), L[(L.early)&(L.cat=='4+ fine moves')].clk.mean()))
print('time share of long-think seconds by category:'); print((L.groupby('cat').spend.sum()/L.spend.sum()).reindex(order).round(3).to_string())
d.to_csv('/home/claude/lt/classified.csv',index=False)
