import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))  # run from drive_model/
import pandas as pd, numpy as np
g=pd.read_parquet('../data/espn/games/2026.parquet'); g=g[g.completed]
b=pd.read_parquet('box2026.parquet')
fbs=set(g.homeTeam[g.homeFBS])|set(g.awayTeam[g.awayFBS])
rows=[]
for x in g.itertuples():
    bb=b[b.eventId==x.eventId]
    for side in ['home','away']:
        t=getattr(x,side+'Team'); o=getattr(x,('away' if side=='home' else 'home')+'Team')
        m=bb[bb.team.str.startswith(t)]
        if len(m)>1: m=m.iloc[[m.team.str.len().argmin()]]
        if len(m)!=1: continue
        s=m.iloc[0]
        try:
            ca,pa=map(int,s.completionAttempts.split('/')); ra=int(s.rushingAttempts); ty=int(s.totalYards)
            tc,ta=map(int,s.thirdDownEff.split('-'))
        except: continue
        rows.append(dict(eventId=x.eventId,date=x.date,off=t if t in fbs else 'FCS',dfn=o if o in fbs else 'FCS',
            home=0 if x.neutralSite else (1 if side=='home' else -1),
            pts=getattr(x,side+'Points'), plays=ra+pa, yds=ty, ypp=ty/(ra+pa), rush_ypc=int(s.rushingYards)/max(ra,1),
            pass_ypa=int(s.netPassingYards)/max(pa,1), third=tc/max(ta,1), third_att=ta, to=int(s.turnovers or 0)))
d=pd.DataFrame(rows); d.to_parquet('teamgames.parquet'); print(len(d), d.eventId.nunique())
