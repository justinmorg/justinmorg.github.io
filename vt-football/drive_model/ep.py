import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
D=pd.read_parquet('drives2026.parquet')
D['pts']=np.where(D.result=='TD',np.where(D.pts>=6,D.pts.clip(upper=8),0),np.where((D.result=='FG')&(D.pts==3),3,0)).astype(float)
D=D[D.ytg.notna()&(D.ytg.between(1,99))].copy()
g=pd.read_parquet('../data/espn/games/2026.parquet'); fbs=set(g.homeTeam[g.homeFBS])|set(g.awayTeam[g.awayFBS])
D['offT']=D.off.where(D.off.isin(fbs),'FCS'); D['dfnT']=D.dfn.where(D.dfn.isin(fbs),'FCS')
fit=D[~D.late & (D.offT!='FCS') & (D.dfnT!='FCS')]
# EP curve: points ~ smooth fn of ytg (cubic in ytg, weighted least squares)
X=lambda y: np.c_[np.ones(len(y)), y/100, (y/100)**2, (y/100)**3]
beta=np.linalg.lstsq(X(fit.ytg.values), fit.pts.values, rcond=None)[0]
EP=lambda y: X(np.asarray(y,float))@beta
for y in [10,20,25,35,50,65,75,90]: print(y, round(float(EP([y])[0]),2), 'binned', round(fit[fit.ytg.between(y-4,y+4)].pts.mean(),2), len(fit[fit.ytg.between(y-4,y+4)]))
D['ep']=EP(D.ytg); D['res']=D.pts-D.ep
D.to_parquet('drives_ep.parquet'); np.save('beta.npy',beta)
