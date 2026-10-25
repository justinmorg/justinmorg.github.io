import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
p=pd.read_parquet('pbp2026.parquet').replace({'offense':{'Pitt':'Pittsburgh'},'defense':{'Pitt':'Pittsburgh'}})
g=pd.read_parquet('../data/espn/games/2026.parquet'); g=g[g.completed]
fbs=set(g.homeTeam[g.homeFBS])|set(g.awayTeam[g.awayFBS])
gi=g.set_index('eventId')
p['gid']=p.gameId.astype(int)
p=p.reset_index(drop=True); p['db']=p.type.eq('P'); p['isR']=p.type.eq('R')
p['rs']=p.success.astype(float).where(p.isR); p['ps']=p.success.astype(float).where(p.db)
a=p.groupby(['gid','offense','defense']).agg(n=('success','size'),sr=('success','mean'),xr=('explosive','mean'),
    rsr=('rs','mean'), psr=('ps','mean'),
    nr=('isR','sum'), npass=('db','sum'), sk=('sack','sum')).reset_index()
a['skr']=a.sk/a.npass.clip(lower=1)
def home(r):
    x=gi.loc[r.gid]; 
    return 0 if x.neutralSite else (1 if x.homeTeam==r.offense else -1)
a['home']=a.apply(home,axis=1); a['date']=a.gid.map(gi.date)
a['off']=a.offense.where(a.offense.isin(fbs),'FCS'); a['dfn']=a.defense.where(a.defense.isin(fbs),'FCS')
teams=sorted(set(a.off)|set(a.dfn)); ix={t:i for i,t in enumerate(teams)}; n=len(teams)
def fit(df,stat,wcol,lam):
    X=np.zeros((len(df),2*n+1))
    for k,(o,de,h) in enumerate(zip(df.off,df.dfn,df.home)): X[k,ix[o]]=1; X[k,n+ix[de]]=1; X[k,2*n]=h
    df=df[df[stat].notna()]; X=X[:len(X)][df.index.map(lambda i: True).values] if False else X
    y=df[stat].values; W=df[wcol].values.astype(float); mu=np.average(y,weights=W)
    Xs=X[[list(a.index if False else df.index).index(i) for i in df.index]] if False else X
    A=X.T@(X*W[:,None])+lam*np.eye(2*n+1)*np.r_[np.ones(2*n),0]; c=np.linalg.solve(A,X.T@(W*(y-mu)))
    return mu,c[:n],c[n:2*n],c[2*n]
specs={'sr':('n',60),'xr':('n',60),'rsr':('nr',40),'psr':('npass',40),'skr':('npass',60)}
a=a.dropna(subset=['rsr','psr']).reset_index(drop=True)
vt=a[a.defense=='Virginia Tech'].sort_values('date')
out=[]
for x in vt.itertuples():
    rest=a[a.gid!=x.gid].reset_index(drop=True); r={'opp':x.offense,'n':x.n}
    for s,(w,l) in specs.items():
        mu,O,D,h=fit(rest,s,w,l); r[s]=getattr(x,s); r[s+'_exp']=mu+O[ix[x.off]]+h*x.home
    out.append(r)
o=pd.DataFrame(out); pd.set_option('display.width',250); print(o.round(3).to_string())
F=[t for t in teams if t!='FCS']
for s,(w,l) in specs.items():
    mu,O,D,h=fit(a,s,w,l); dr=pd.Series(D,index=teams)[F]
    asc = s!='skr'
    print(s, f'mu {mu:.3f} VT def {D[ix["Virginia Tech"]]:+.3f} rank {int(dr.rank(ascending=asc)["Virginia Tech"])}/{len(F)}  Clemson off {O[ix["Clemson"]]:+.3f} rank {int(pd.Series(O,index=teams)[F].rank(ascending=not asc)["Clemson"])}')
o.to_csv('vt_def_pbp.csv',index=False)
