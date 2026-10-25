import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import json,urllib.request,io,math,time,os,pandas as pd,numpy as np
from concurrent.futures import ThreadPoolExecutor
def get(u,raw=False):
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'vt-football research'}),timeout=120) as r:
        b=r.read(); return b if raw else json.loads(b)
V=pd.read_csv('venues.csv'); G=pd.read_csv('game_venues.csv')
states=sorted(set(V.state.dropna()))
st=[]
for s in states:
    try:
        for f in get(f'https://mesonet.agron.iastate.edu/geojson/network/{s}_ASOS.geojson')['features']:
            p=f['properties']; lo,la=f['geometry']['coordinates']; st.append(dict(sid=p['sid'],la=la,lo=lo,arch_end=p.get('archive_end')))
    except Exception as e: print('net fail',s,e)
S=pd.DataFrame(st); S=S[S.arch_end.isna()]  # still reporting
def near(r):
    if pd.isna(r.lat): return pd.Series([None,None])
    d=np.hypot((S.la-r.lat)*111,(S.lo-r.lon)*111*math.cos(math.radians(r.lat)))
    i=d.idxmin(); return pd.Series([S.loc[i,'sid'],round(d[i],1)])
V[['sid','km']]=V.apply(near,axis=1); V.to_csv('venues.csv',index=False)
print(V.km.describe().round(1)); print(V.sort_values('km',ascending=False).head(5)[['vname','city','state','sid','km']])
os.makedirs('asos',exist_ok=True)
def pull(sid):
    p=f'asos/{sid}.csv'
    if os.path.exists(p): return
    u=('https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station='+sid+'&data=tmpf&data=sknt&data=gust&data=p01i&data=wxcodes'
       '&year1=2026&month1=8&day1=25&year2=2026&month2=10&day2=26&tz=Etc/UTC&format=onlycomma&missing=M&trace=0.0001&report_type=3')
    for k in range(3):
        try: open(p,'wb').write(get(u,True)); return
        except Exception as e: time.sleep(3)
    print('pull fail',sid)
with ThreadPoolExecutor(4) as ex: list(ex.map(pull, V.sid.dropna().unique()))
print('stations pulled', len(os.listdir('asos')))
