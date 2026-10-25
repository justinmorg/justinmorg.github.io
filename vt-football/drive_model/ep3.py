import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
from sklearn.isotonic import IsotonicRegression
D=pd.read_parquet('drives_ep.parquet')
fit=D[~D.late & (D.offT!='FCS') & (D.dfnT!='FCS')]
y=fit.ytg.values.astype(float); p=fit.pts.values
iso=IsotonicRegression(increasing=False, out_of_bounds='clip').fit(y,p)
grid=np.arange(1,100); f=iso.predict(grid)
# light smoothing of the step function (bw 3 yds), keeps monotone
sm=np.array([np.average(f, weights=np.exp(-0.5*((grid-g0)/3)**2)) for g0 in grid])
EPtab=pd.Series(f,index=grid); EPtab.to_csv('ep_curve.csv')
for t in [5,10,20,25,30,35,40,50,60,65,70,75,80,90,95]: print(t, round(EPtab[t],2), 'raw', round(p[(y>=t-2)&(y<=t+2)].mean(),2))
D['ep']=D.ytg.round().clip(1,99).astype(int).map(EPtab); D['res']=D.pts-D.ep
D.to_parquet('drives_ep.parquet')
print('mean pts',round(fit.pts.mean(),3),'mean ep',round(D.loc[fit.index,'ep'].mean(),3))
