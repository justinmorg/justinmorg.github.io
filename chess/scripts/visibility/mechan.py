import pandas as pd, numpy as np, json, glob
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
R=pd.DataFrame([json.loads(l) for f in ['mech0.jsonl','mech1.jsonl'] for l in open(f)])
R[['gid','ply']]=R.k.str.split(':',expand=True); R['ply']=R.ply.astype(int)
m=pd.read_parquet('seg.parquet')
d=R.merge(m[['gid','ply','mat','score','cost','queens','phase','clock','pmat','my']],on=['gid','ply'])
q=d[d.loss6>=2].copy()      # lost >= 2 pawns of material within three moves on the engine line
def cls(r):
    if isinstance(r.tgt,str):
        if r.nx_def==0: c='A undefended'
        elif r.min_att < {'pawn':1,'knight':3,'bishop':3,'rook':5,'queen':9}[r.tgt_piece]: c='B attacked by a cheaper piece'
        elif r.nx_att>r.nx_def: c='C attacked more times than defended'
        else: c='D enough defenders on paper (pin/overload/other)'
        return c
    if isinstance(r.setup_disc_targets,list) and len(r.setup_disc_targets)>0: return 'E discovered attack'
    if r.setup_mover_targets>=2 or (r.setup_check and r.setup_new_targets>=1): return 'F fork / double attack'
    return 'G other (mate threat, trapped piece, longer combination)'
q['mech']=q.apply(cls,axis=1)
q['king_only']=q.apply(lambda r: isinstance(r.defx_kinds,list) and r.defx_kinds==['king'],axis=1)
def origin(r):
    if not isinstance(r.tgt,str): return '-'
    if not r.tgt_was_mine_before: return 'the piece you just moved'
    if isinstance(r.ep_before_my_move,dict) and r.tgt in r.ep_before_my_move: return 'was already en prise (standing threat)'
    if r.nx_def_before is not None and r.nx_def_before>r.nx_def: return 'your move took away a defender'
    if r.nx_att_before is not None and r.nx_att>r.nx_att_before: return 'your move opened a line onto it'
    return 'other'
q['origin']=q.apply(origin,axis=1)
print('errors classified',len(d),' with >=2 material lost in 3 moves:',len(q), f'({len(q)/len(d):.0%})')
for scope,s in [('ALL GAMES',q),('LOST GAMES',q[q.score==0])]:
    t=pd.crosstab(s.mech,s.mat,normalize='columns').mul(100).round(0); t['all']=s.mech.value_counts(normalize=True).mul(100).round(0)
    print('\n',scope,'mechanism share by material (%)'); print(t)
    print(pd.crosstab(s.mat,'n'))
s=q
c=s[s.mech.str[0]=='C']; print('\nC: king the only defender share by material'); print(c.groupby('mat').king_only.mean().mul(100).round(0))
print('\norigin of direct hangs by material'); dd=s[s.mech.str[0].isin(list('ABCD'))]; print(pd.crosstab(dd.origin,dd.mat,normalize='columns').mul(100).round(0))
print('\nshare of all errors that are quick material losses, by material'); print((d.assign(q=d.loss6>=2).groupby('mat').q.mean()*100).round(0))
q.to_parquet('mechq.parquet')
