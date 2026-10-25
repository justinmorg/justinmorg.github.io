import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
D=pd.read_parquet('drives_ep.parquet'); D['date']=pd.to_datetime(D.date)
A=D[~D.late].reset_index(drop=True)
teams=sorted(set(A.offT)|set(A.dfnT)); ix={t:i for i,t in enumerate(teams)}; n=len(teams)
def X(df):
    M=np.zeros((len(df),2*n+1))
    for k,(o,d,h) in enumerate(zip(df.offT,df.dfnT,df.home)): M[k,ix[o]]=1; M[k,n+ix[d]]=1; M[k,2*n]=h
    return M
XA=X(A)
def fit(mask,lam=40):
    M=XA[mask]; y=A.res.values[mask]
    c=np.linalg.solve(M.T@M+lam*np.eye(2*n+1)*np.r_[np.ones(2*n),0], M.T@y); return c[:n],c[n:2*n],c[2*n]
vt=A[A.dfn=='Virginia Tech']; rows=[]
for eid,gg in vt.groupby('eid'):
    O,Dd,h=fit((A.eid!=eid).values)
    o=gg.offT.iloc[0]; adj=O[ix[o]]+h*gg.home.iloc[0]
    late=D[(D.eid==eid)&(D.dfn=='Virginia Tech')&D.late]
    rows.append(dict(date=gg.date.iloc[0].strftime('%m-%d'),opp=gg.off.iloc[0],drives=len(gg),start=round(100-gg.ytg.mean(),1),
        short=int((gg.ytg<=50).sum()),pts=gg.pts.sum(),ep_fp=gg.ep.sum(),off_adj=adj*len(gg),exp=gg.ep.sum()+adj*len(gg),late_pts=late.pts.sum()))
r=pd.DataFrame(rows).sort_values('date'); r['diff']=r.pts-r.exp; r['per_drive']=r['diff']/r.drives
pd.set_option('display.width',250); print(r.round(2).to_string(index=False))
print('tot', r[['drives','pts','ep_fp','exp','diff']].sum().round(1).to_dict())
O,Dd,h=fit(np.ones(len(A),bool))
F=[t for t in teams if t!='FCS']; ds=pd.Series(Dd,index=teams)[F]
print('VT def pts/drive vs exp (season, opp+FP adj):',round(Dd[ix['Virginia Tech']],3),'rank',int(ds.rank()['Virginia Tech']),'/',len(F),' home adv',round(h,3))
print(ds.sort_values().head(5).round(2).to_dict())
r.to_csv('vt_def_drive_ep.csv',index=False)
# check Clemson game drives
print(A[(A.dfn=='Virginia Tech')&(A.off=='Clemson')][['q','clock','ytg','result','pts','ep']].to_string())
