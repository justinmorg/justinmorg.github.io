import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import json,glob,urllib.request,urllib.parse,time,math,pandas as pd
ST={'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'District of Columbia'}
def get(u):
    for k in range(5):  # the geocoder drops ~20% of requests; retry with backoff
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'vt-football research'}),timeout=60) as r: return json.load(r)
        except Exception:
            if k==4: raise
            time.sleep(2+2*k)
rows={}; games=[]
for f in glob.glob('espn_pbp/raw/*.json'):
    s=json.load(open(f)); c=s['header']['competitions'][0]; v=s['gameInfo'].get('venue',{})
    games.append(dict(eid=int(c['id']),kick=c['date'],venue=v.get('id'),vname=v.get('fullName')))
    a=v.get('address',{}); rows[v.get('id')]=dict(venue=v.get('id'),vname=v.get('fullName'),city=a.get('city'),state=a.get('state'),country=a.get('country'))
V=pd.DataFrame(rows.values())
DOME=['Dome','Ford Field','Lucas Oil','Allegiant','AT&T Stadium','NRG','Mercedes-Benz','U.S. Bank','State Farm Stadium','Caesars','Superdome','Tropicana','Carrier','JMA','FargoDome','Holt Arena','Kibbie']
V['dome']=V.vname.fillna('').apply(lambda n:any(k.lower() in n.lower() for k in DOME))
lat=[];lon=[]
for r in V.itertuples():
    la=lo=None
    try:
        res=get('https://geocoding-api.open-meteo.com/v1/search?'+urllib.parse.urlencode(dict(name=r.city,count=20,country='US' if (r.country or 'USA') in ('USA','US') else '')))['results']
        want=ST.get(r.state,r.state)
        m=[x for x in res if x.get('admin1')==want] or res
        la,lo=m[0]['latitude'],m[0]['longitude']
    except Exception as e: print('geo fail',r.vname,r.city,r.state,e)
    lat.append(la);lon.append(lo); time.sleep(0.15)
V['lat']=lat;V['lon']=lon
V.to_csv('venues.csv',index=False); pd.DataFrame(games).to_csv('game_venues.csv',index=False)
print(V.dome.sum(),'domes:',V[V.dome].vname.tolist()); print(V[V.lat.isna()])
