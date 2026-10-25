import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np, os
V=pd.read_csv('venues.csv').set_index('venue'); G=pd.read_csv('game_venues.csv')
cache={}
def st(sid):
    if sid not in cache:
        p=f'asos/{sid}.csv'
        df=pd.read_csv(p,na_values='M') if os.path.exists(p) and os.path.getsize(p)>100 else None
        if df is not None: df['valid']=pd.to_datetime(df.valid,utc=True)
        cache[sid]=df
    return cache[sid]
rows=[]
for g in G.itertuples():
    v=V.loc[g.venue] if g.venue in V.index else None
    r=dict(eid=g.eid,vname=g.vname)
    if v is None or pd.isna(v.state) or v.km>40: rows.append(r); continue
    if v.dome: r.update(wind=0,gust=0,precip=0,rain=0,temp=70,dome=1); rows.append(r); continue
    df=st(v.sid); k=pd.Timestamp(g.kick)
    if df is None: rows.append(r); continue
    w=df[(df.valid>=k-pd.Timedelta('30min'))&(df.valid<=k+pd.Timedelta('3.5h'))]
    if len(w)<2: rows.append(r); continue
    wx=w.wxcodes.fillna('')
    r.update(wind=w.sknt.mean()*1.151, gust=w.gust.max()*1.151 if w.gust.notna().any() else w.sknt.max()*1.151,
             precip=w.p01i.fillna(0).clip(lower=0).sum(), rain=wx.str.contains('RA|DZ|SN|TS').mean(), temp=w.tmpf.mean(), dome=0)
    rows.append(r)
W=pd.DataFrame(rows); W.to_csv('game_weather.csv',index=False)
print(W.describe().round(2)); print('missing',W.wind.isna().sum())
print(W.sort_values('precip',ascending=False).head(8).round(2).to_string())
print(W.sort_values('wind',ascending=False).head(6).round(1).to_string())
