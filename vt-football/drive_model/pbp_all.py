import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import sys, os, pandas as pd, numpy as np
sys.path.insert(0,'..')
import espn_pbp as E
E.BASE=os.path.abspath('espn_pbp')
from concurrent.futures import ThreadPoolExecutor
g=pd.read_parquet('../data/espn/games/2026.parquet'); g=g[g.completed]
def one(eid):
    try:
        s=E.load(eid); return E.parse(eid,s)[1]
    except Exception as e: return None
with ThreadPoolExecutor(12) as ex: res=list(ex.map(one,g.eventId))
p=pd.concat([r for r in res if r is not None]); print('games',sum(r is not None for r in res))
p=p[p.type.isin(['R','P'])&p.down.notna()&~p.text.str.contains('NO PLAY|kneel',case=False,na=False)].copy()
p['yards']=p.yards.fillna(0)
need=np.where(p.down==1,.5,np.where(p.down==2,.7,1.0))*p.distance
p['success']=(p.yards>=need)|(p.scoring&~p.turnover)
p['explosive']=((p.type=='R')&(p.yards>=10))|((p.type=='P')&(p.yards>=20))
p['sack']=p.passResult.eq('SACK')
p.to_parquet('pbp2026.parquet'); print(len(p))
