import pandas as pd, numpy as np, json, glob
rows=[json.loads(l) for f in glob.glob('out*.jsonl') for l in open(f)]
P=pd.DataFrame(rows).drop_duplicates('key'); P[['mode','gid','ply']]=P.key.str.split(':',expand=True); P['ply']=P.ply.astype(int)
pre=P[P['mode']=='pre'][['gid','ply','traj','mate']].rename(columns={'traj':'p','mate':'pm'})
post=P[P['mode']=='post'][['gid','ply','traj','mate']].rename(columns={'traj':'q','mate':'qm'})
m=pd.read_parquet('seg.parquet').sort_values(['gid','ply'])
m['next_pmat']=m.groupby('gid').pmat.shift(-1); m['next_ply']=m.groupby('gid').ply.shift(-1)
m['next_cost']=m.groupby('gid').cost.shift(-1); m['next_wp']=m.groupby('gid').wp_before.shift(-1)
d=pre.merge(post,on=['gid','ply']).merge(m,on=['gid','ply'])
d=d[d.err]
def classify(r):
    p,q,b=r.p,r.q,r.pmat
    n=min(len(q),len(p)-1)
    diff=[q[j]-p[j+1] for j in range(n)]
    if r.qm=='me' and r.pm!='me': return len(q)-1, 'mate'
    for j,x in enumerate(diff):
        if x<=-2 and all(y<=-1 for y in diff[j:]): 
            kind='lost material' if q[j]-b<=-2 else 'missed a win of material'
            if q[j]-b<=-2 and p[j+1]-b>=2: kind='lost material'
            return j, kind
    return None, 'none'
res=[classify(r) for r in d.itertuples()]
d['j']=[a for a,_ in res]; d['kind']=[b for _,b in res]
def bucket(j,kind):
    if kind=='none': return '5 never shows as material (15 moves)'
    j=int(j); return ('1 their very next move' if j==0 else '2 within 2-3 moves' if j<=2 else '3 within 4-7 moves' if j<=6 else '4 within 8-15 moves')
d['vis']=[bucket(a,b) for a,b in zip(d.j,d.kind)]
# did the real opponent actually cash in material by my next turn?
d['real_next_drop']=(d.next_ply==d.ply+2)&(d.next_pmat-d.pmat<=-2)
d.to_parquet('paired.parquet')
print('paired errors:',len(d))
t=d.groupby('vis').agg(n=('cost','size'),cost=('cost','sum'))
t['share of errors %']=100*t.n/t.n.sum(); t['share of cost %']=100*t.cost/t.cost.sum()
L=d[d.score==0]; t['share of cost, lost games %']=100*L.groupby('vis').cost.sum()/L.cost.sum()
t['avg size (pts)']=100*t.cost/t.n
print(t.drop(columns='cost').round(1).to_string())
print('\nkind x vis (% of errors)'); print((pd.crosstab(d.vis,d.kind,normalize=True)*100).round(1))
print('\nreal opponent took >=2 material by my next turn, by class:'); print((d.groupby('vis').real_next_drop.mean()*100).round(1))
for c in ('mat','queens','phase','clock'):
    print('\n',c); print((pd.crosstab(d[c],d.vis,normalize='index')*100).round(0))
