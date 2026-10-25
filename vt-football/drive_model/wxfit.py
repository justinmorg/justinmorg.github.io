import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
D=pd.read_parquet('drives_ep.parquet'); W=pd.read_csv('game_weather.csv').set_index('eid')
A=D[~D.late].reset_index(drop=True)
w=W.reindex(A.eid)
A['w_wind']=np.clip(w.wind.values-10,0,None)        # mph above 10
A['w_rain']=w.rain.values                            # share of obs with rain/storms
A['w_cold']=np.clip(50-w.temp.values,0,None)
for c in ['w_wind','w_rain','w_cold']: A[c]=A[c].fillna(0)
teams=sorted(set(A.offT)|set(A.dfnT)); ix={t:i for i,t in enumerate(teams)}; n=len(teams)
WX=['w_wind','w_rain','w_cold']
def build(df):
    M=np.zeros((len(df),2*n+1+len(WX)))
    for k,(o,d,h) in enumerate(zip(df.offT,df.dfnT,df.home)): M[k,ix[o]]=1; M[k,n+ix[d]]=1; M[k,2*n]=h
    M[:,2*n+1:]=df[WX].values; return M
M=build(A)
def fit(mask,lam=40):
    X=M[mask]; y=A.res.values[mask]; pen=np.r_[np.ones(2*n),0,np.zeros(len(WX))]
    return np.linalg.solve(X.T@X+lam*np.diag(pen),X.T@y)
c=fit(np.ones(len(A),bool)); beta=c[2*n+1:]
# bootstrap by game for SEs on weather terms
rng=np.random.default_rng(0); eids=A.eid.unique(); bs=[]
for b in range(60):
    pick=rng.choice(eids,len(eids)); cnt=pd.Series(pick).value_counts()
    wts=A.eid.map(cnt).fillna(0).values; X=M*np.sqrt(wts)[:,None]; y=A.res.values*np.sqrt(wts)
    pen=np.r_[np.ones(2*n),0,np.zeros(len(WX))]; bs.append(np.linalg.solve(X.T@X+40*np.diag(pen),X.T@y)[2*n+1:])
se=np.std(bs,axis=0)
for k,s,e in zip(WX,beta,se): print(f'{k}: {s:+.3f} pts/drive per unit (se {e:.3f})')
A['wx_eff']=A[WX].values@beta
g=A.groupby('eid').agg(eff=('wx_eff','mean')); g=g.join(W[['vname','wind','gust','rain','temp']])
print('\nmost weather-suppressed games (pts/drive):'); print(g.sort_values('eff').head(8).round(2).to_string())
print('share of games with effect below -0.2/drive:', round((g.eff<-0.2).mean(),3))
# VT defense game table with weather
vt=A[A.dfn=='Virginia Tech']; rows=[]
for eid,gg in vt.groupby('eid'):
    cc=fit((A.eid!=eid).values); O=cc[:n]; h=cc[2*n]; b=cc[2*n+1:]
    adj=O[ix[gg.offT.iloc[0]]]+h*gg.home.iloc[0]
    wx=(gg[WX].values@b).sum()
    exp0=gg.ep.sum()+adj*len(gg)
    rows.append(dict(opp=gg.off.iloc[0],drives=len(gg),pts=gg.pts.sum(),exp_noWx=exp0,wx=wx,exp=exp0+wx))
r=pd.DataFrame(rows); r['diff']=r.pts-r.exp; print(r.round(1).to_string(index=False)); print('total diff',round(r['diff'].sum(),1),'per drive',round(r['diff'].sum()/r.drives.sum(),3))
D_all=c[n:2*n]; F=[t for t in teams if t!='FCS']; ds=pd.Series(D_all,index=teams)[F]
print('VT D/drive weather-adjusted, all games:',round(D_all[ix['Virginia Tech']],3),'rank',int(ds.rank()['Virginia Tech']),'/',len(F))
# defenses most flattered by weather this season
A['flat']=A.wx_eff; fl=A[A.dfnT!='FCS'].groupby('dfn').flat.sum().sort_values()
print('\ndefenses with most weather help (total pts):'); print(fl.head(6).round(1).to_dict()); print('VT:',round(fl['Virginia Tech'],1))
A.to_parquet('drives_wx.parquet'); np.save('wx_beta.npy',beta)
