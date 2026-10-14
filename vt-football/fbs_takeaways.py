"""FBS-wide takeaways per game by season (ESPN boxes, data/espn/box) with VT alongside.
Writes data/derived/fbs_takeaways_by_season.csv and fbs_team_takeaways_by_season.csv.
A team-season counts if the team played 4+ games vs anyone (FCS games included)."""
import pandas as pd,glob
b=pd.concat(pd.read_parquet(f) for f in sorted(glob.glob('data/espn/box/*.parquet')))
o=b[['eventId','teamId','intThrown','fumblesLost','turnovers']].rename(columns={'teamId':'oppId','intThrown':'tkInt','fumblesLost':'tkFum','turnovers':'tk'})
t=b.merge(o,on=['eventId','oppId'])
f=t[t.fbs & t.tk.notna()]
team=f.groupby(['season','teamId','team']).agg(g=('tk','size'),tk=('tk','sum'),ti=('tkInt','sum'),tf=('tkFum','sum')).reset_index()
team['pg']=team.tk/team.g
team=team[team.g>=4]
nat=team.groupby('season').agg(teams=('pg','size'),fbsAvg=('pg','mean'),fbsMedian=('pg','median'),p10=('pg',lambda x:x.quantile(.1)),p90=('pg',lambda x:x.quantile(.9))).reset_index()
nat['fbsInt']=team.groupby('season').apply(lambda x:(x.ti/x.g).mean()).values
nat['fbsFum']=team.groupby('season').apply(lambda x:(x.tf/x.g).mean()).values
vt=team[team.teamId==259].set_index('season')
team['rank']=team.groupby('season').pg.rank(ascending=False,method='min')
nat['vtESPN']=nat.season.map(vt.pg)
nat['vtRank']=nat.season.map(team[team.teamId==259].set_index('season')['rank'])
off=pd.read_csv('data/derived/vt_takeaways_by_season.csv').set_index('season')
nat['vtRepo']=nat.season.map(off.takeawaysPerGame)
nat['vtMinusAvg']=nat.vtRepo-nat.fbsAvg
pd.set_option('display.width',200)
print(nat.round(2).to_string(index=False))
# ESPN vs official per game check for VT
g=pd.read_csv('data/derived/vt_takeaways_by_game.csv'); g=g[g.season>=2010]
e=f[f.teamId==259][['date','opp','tk']]
m=g.merge(e,on='date')
print('VT games matched',len(m),'exact',(m.takeaways==m.tk).mean().round(3),'official sum',m.takeaways.sum(),'espn',m.tk.sum())
print('box-source only exact',(m[m.source=='box'].takeaways==m[m.source=='box'].tk).mean().round(3), len(m[m.source=='box']))
nat.round(3).to_csv('data/derived/fbs_takeaways_by_season.csv',index=False)
team.round(3).to_csv('data/derived/fbs_team_takeaways_by_season.csv',index=False)
# era summary
for a,z in [(2010,2014),(2015,2019),(2020,2024),(2025,2026)]:
  x=nat[(nat.season>=a)&(nat.season<=z)]; print(a,z,'fbs',x.fbsAvg.mean().round(2),'vt',x.vtRepo.mean().round(2))
