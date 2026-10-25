import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
D=pd.read_parquet('drives_ep.parquet'); EP=pd.read_csv('ep_curve.csv',index_col=0).iloc[:,0]
A=D[~D.late].reset_index(drop=True)
bc=A[(A.dfn=='Virginia Tech')&(A.off=='Boston College')].eid.unique()
A=A[~A.eid.isin(bc)].reset_index(drop=True)          # drop the rain game
teams=sorted(set(A.offT)|set(A.dfnT)); ix={t:i for i,t in enumerate(teams)}; n=len(teams)
M=np.zeros((len(A),2*n+1))
for k,(o,d,h) in enumerate(zip(A.offT,A.dfnT,A.home)): M[k,ix[o]]=1; M[k,n+ix[d]]=1; M[k,2*n]=h
c=np.linalg.solve(M.T@M+40*np.eye(2*n+1)*np.r_[np.ones(2*n),0],M.T@A.res.values); O,Dd,h=c[:n],c[n:2*n],c[2*n]
vtD=Dd[ix['Virginia Tech']]; print('VT D/drive',round(vtD,3),'home',round(h,3))
# typical drive count per team-game and start distribution
tg=A.groupby(['eid','off']).agg(nd=('pts','size'),pts=('pts','sum'),ep=('ep','sum'),start=('ytg','mean'))
print('drives/team-game pctiles', tg.nd.quantile([.1,.25,.5,.75,.9]).to_dict(), 'mean start ytg', round(A.ytg.mean(),1))
# game-level residual SD (actual - model expectation)
A['fit']=A.ep+M[:, :2*n+1]@c
g=A.groupby(['eid','off']).agg(nd=('pts','size'),pts=('pts','sum'),fit=('fit','sum'))
r=g.pts-g.fit; print('game resid sd',round(r.std(),2),'per sqrt drive',round((r/np.sqrt(g.nd)).std(),2))
sdpd=(r/np.sqrt(g.nd)).std()
base=A.ytg.values
def ep_at(shift):  # shift = yards closer to goal than an average FBS start
    y=np.clip(np.round(base-shift),1,99).astype(int); return EP.loc[y].mean(), 100-y.mean()
games=[('SMU',-1),('Stanford',1),('Miami',-1),('Virginia',1)]
for t,vthome in games:
    off=O[ix[t]]; hh=h*(-vthome)  # opponent home when VT away
    print(f'\n{t}: off {off:+.2f}/drive, VT D {vtD:+.2f}, site {hh:+.2f}')
    for shift,lab in [(-5,'poor'),(0,'avg'),(5,'good'),(10,'great')]:
        e,st=ep_at(shift)
        line=[]
        for nd in (10,12,14):
            mu=nd*(e+off+vtD+hh); line.append(f'{nd}dr {mu:4.1f} ({max(0,mu-1.28*sdpd*np.sqrt(nd)):.0f}-{mu+1.28*sdpd*np.sqrt(nd):.0f})')
        print(f'  start own {st:4.1f} [{lab}]: '+' | '.join(line))
# what drive counts / starts did VT opponents get?
v=D[(D.dfn=='Virginia Tech')&~D.late].groupby('off').agg(nd=('pts','size'),start=('ytg',lambda s:100-s.mean()))
print(v.round(1)); print('opp offenses drive counts season:',{t: A[A.off==t].groupby('eid').size().mean().round(1) for t,_ in games})
print('opp offense start pos season:',{t: round(100-A[A.off==t].ytg.mean(),1) for t,_ in games})
print('VT offense drives/game:', A[A.off=='Virginia Tech'].groupby('eid').size().mean().round(1))
