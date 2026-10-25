import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
d=pd.read_parquet('teamgames.parquet')
teams=sorted(set(d.off)|set(d.dfn)); ix={t:i for i,t in enumerate(teams)}; n=len(teams)
def fit(df, stat, lam=None, w=None):
    X=np.zeros((len(df),2*n+1)); 
    for k,(o,de,h) in enumerate(zip(df.off,df.dfn,df.home)): X[k,ix[o]]=1; X[k,n+ix[de]]=1; X[k,2*n]=h
    y=df[stat].values; mu=np.average(y,weights=w) if w is not None else y.mean()
    lam=lam or {'pts':4,'ypp':4,'rush_ypc':5,'pass_ypa':5,'third':6,'to':8}[stat]
    W=np.ones(len(df)) if w is None else w
    A=X.T@(X*W[:,None])+lam*np.eye(2*n+1)*np.r_[np.ones(2*n),0]; c=np.linalg.solve(A,X.T@(W*(y-mu)))
    return mu,c[:n],c[n:2*n],c[2*n]   # off rating (+good), def rating (+ = allows more)
stats=['pts','ypp','rush_ypc','pass_ypa','third','to']
vt=d[d.dfn=='Virginia Tech'].sort_values('date')
out=[]
for x in vt.itertuples():
    rest=d[d.eventId!=x.eventId]
    r={'opp':x.off,'date':str(x.date)[:10]}
    for s in stats:
        w = rest.third_att.values.astype(float) if s=='third' else None
        mu,O,D,h=fit(rest,s,w=w)
        exp_avg=mu+O[ix[x.off]]+h*x.home          # vs an average FBS defense
        r[s]=getattr(x,s); r[s+'_exp']=exp_avg
    out.append(r)
o=pd.DataFrame(out); o.to_csv('vt_def_games.csv',index=False)
pd.set_option('display.width',250)
for s in stats: o[s+'_d']=o[s]-o[s+'_exp']
print(o[['date','opp']+[c for s in stats for c in (s,s+'_exp')]].round(2).to_string())
# season-level def ratings with all games
fbs=[t for t in teams if t!='FCS']
for s in stats:
    w = d.third_att.values.astype(float) if s=='third' else None
    mu,O,D,h=fit(d,s,w=w)
    dr=pd.Series(D,index=teams)[fbs].sort_values()
    if s=='to': dr=dr.sort_values(ascending=False)
    orr=pd.Series(O,index=teams)[fbs].sort_values(ascending=(s=='to'))
    print(f"{s}: mu {mu:.2f} | VT def {D[ix['Virginia Tech']]:+.2f} rank {list(dr.index).index('Virginia Tech')+1}/{len(fbs)} | VT off {O[ix['Virginia Tech']]:+.2f} rank {list(orr.index).index('Virginia Tech')+1} | Clemson off {O[ix['Clemson']]:+.2f} rank {list(orr.index).index('Clemson')+1} | Clemson def rank {list(dr.index).index('Clemson')+1}")
