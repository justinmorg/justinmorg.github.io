import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import sys, json, pandas as pd
sys.path.insert(0,'..')
from espn import get
from concurrent.futures import ThreadPoolExecutor
g=pd.read_parquet('../data/espn/games/2026.parquet'); g=g[g.completed]
SUM="https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={}"
def one(eid):
    try:
        d=get(SUM.format(eid)); out=[]
        for t in d['boxscore']['teams']:
            s={x['name']:x.get('displayValue') for x in t['statistics']}
            s['team']=t['team']['displayName']; s['eventId']=eid; out.append(s)
        return out
    except Exception as e: return []
rows=[]
with ThreadPoolExecutor(12) as ex:
    for r in ex.map(one, g.eventId): rows+=r
df=pd.DataFrame(rows); df.to_parquet('box2026.parquet'); print(df.shape); print(df.columns.tolist()); print(df.iloc[0])
