import pandas as pd, chess, chess.engine, json, sys, os
d=pd.read_csv('deepjobs.csv',dtype={'gid':str}); sh,ns=int(sys.argv[1]),int(sys.argv[2]); d=d[d.index%ns==sh]
out=f'deep{sh}.jsonl'; done=set()
if os.path.exists(out): done={json.loads(l)['k'] for l in open(out)}
e=chess.engine.SimpleEngine.popen_uci('/home/claude/sf/x/usr/games/stockfish'); e.configure({'Threads':1,'Hash':128})
def ev(b, me):
    s=e.analyse(b, chess.engine.Limit(depth=16))['score'].pov(me); return s.score(mate_score=10000)
with open(out,'a') as fo:
    for r in d.itertuples():
        k=f'{r.kind}:{r.gid}:{r.ply}'
        if k in done: continue
        b=chess.Board(r.fen); me=b.turn; res={'k':k,'before':ev(b,me)}
        a=b.copy(); a.push(chess.Move.from_uci(r.uci)); res['after']=ev(a,me)
        if r.kind=='gift':
            p=chess.Board(r.prev_fen); p.push(chess.Move.from_uci(r.prev_uci)); res['prevafter']=ev(p,me)
        fo.write(json.dumps(res)+'\n'); fo.flush()
