import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import json, glob, pandas as pd
g=pd.read_parquet('../data/espn/games/2026.parquet'); g=g[g.completed].set_index('eventId')
fbs=set(g.homeTeam[g.homeFBS])|set(g.awayTeam[g.awayFBS])
def secs(c):
    try: m,s=c.split(':'); return int(m)*60+int(s)
    except: return None
rows=[]
for f in glob.glob('espn_pbp/raw/*.json'):
    s=json.load(open(f)); comp=s['header']['competitions'][0]; eid=int(comp['id'])
    if eid not in g.index: continue
    team={c['id']:c['team']['location'] for c in comp['competitors']}
    hid=next(c['id'] for c in comp['competitors'] if c['homeAway']=='home')
    neutral=bool(g.loc[eid,'neutralSite'])
    prev=(0,0)
    for d in s['drives']['previous']:
        pl=d.get('plays',[])
        if not pl: continue
        if not (d.get('team') or any(p.get('teamParticipants') for p in pl)): continue
        tid=(d.get('team') or {}).get('id') or next((x['id'] for p in pl for x in p.get('teamParticipants',[]) if x.get('type')=='offense'),None); off=team.get(tid); dfn=next((v for k,v in team.items() if k!=tid),None)
        scr=[p for p in pl if (p.get('start') or {}).get('down') and not any(k in (p.get('type') or {}).get('text','') for k in ('Kickoff','Timeout','End Period','Coin Toss','End of'))]
        ytg=(scr[0]['start'].get('yardsToEndzone') if scr else None)
        end=(pl[-1].get('homeScore',prev[0]),pl[-1].get('awayScore',prev[1]))
        ishome= tid==hid
        pts=(end[0]-prev[0]) if ishome else (end[1]-prev[1])
        prev=end
        q=d['start'].get('period',{}).get('number') or pl[0]['period']['number']; clk=secs((d['start'].get('clock') or pl[0].get('clock') or {}).get('displayValue'))
        rows.append(dict(eid=eid,date=g.loc[eid,'date'],off=off,dfn=dfn,home=0 if neutral else (1 if ishome else -1),
            q=q,clock=clk,ytg=ytg,pts=max(pts,0),result=d.get('result'),plays=d.get('offensivePlays')))
D=pd.DataFrame(rows)
D['late']=(D.q.isin([2,4])&(D.clock<=60))|(D.q>4)
D.to_parquet('drives2026.parquet'); print(len(D)); print(D.result.value_counts().head(8)); print(D[D.ytg.isna()].result.value_counts().head())
print(D.groupby('result').pts.mean().round(2))
