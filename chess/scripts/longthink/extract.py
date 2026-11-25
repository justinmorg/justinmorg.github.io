import sys, json, re, random, io, pandas as pd, chess, chess.pgn
sys.path.insert(0,'/home/claude/justinmorg.github.io/chess/scripts')
m=pd.read_csv('/home/claude/features7/moves.csv.gz',low_memory=False)
x=m[(m.tc=='180+2')&m.spend.notna()&m.block.isin(['Y2026','TREAT'])]
lt=x[x.spend>=15]; q=x[(x.spend<=5)&(x.fullmove>=8)].sample(1500,random_state=23)
want={}
for kind,d in (('long',lt),('quick',q)):
    for r in d.itertuples(): want[(r.gid,int(r.ply))]=dict(kind=kind,spend=float(r.spend),fullmove=int(r.fullmove),wp_before=float(r.wp_before),clk=float(r.clk),opp=float(r.opp_clk),block=r.block,wp_after=float(r.wp_after))
gids={g for g,_ in want}
out=open('/home/claude/lt/positions.jsonl','w'); n=0
for f in ('/home/claude/blocks/jamorgan_blitz_2026.pgn','/home/claude/blocks/F.pgn'):
    h=open(f)
    while True:
        gm=chess.pgn.read_game(h)
        if gm is None: break
        gid=gm.headers.get('GameId') or gm.headers.get('Site','').rsplit('/',1)[-1]
        if gid not in gids: continue
        b=gm.board(); ply=0
        for node in gm.mainline():
            ply+=1
            k=(gid,ply)
            if k in want:
                d=dict(want[k]); d.update(gid=gid,ply=ply,fen=b.fen(),played=node.move.uci(),san=b.san(node.move),color='white' if b.turn else 'black')
                out.write(json.dumps(d)+'\n'); n+=1
            b.push(node.move)
print('wrote',n,'of',len(want))
