import sys, json, time, math, chess, chess.engine, os
shard, nsh, budget = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
src=[json.loads(l) for l in open('/home/claude/lt/positions.jsonl')][shard::nsh]
outp=f'/home/claude/lt/mpv_{shard}.jsonl'
done=set()
if os.path.exists(outp):
    for l in open(outp): done.add(json.loads(l)['k'])
wp=lambda cp: 1/(1+math.exp(-0.00368208*cp))
eng=chess.engine.SimpleEngine.popen_uci('/home/claude/sf/x/usr/games/stockfish'); eng.configure({'Threads':1,'Hash':64})
t0=time.time(); out=open(outp,'a'); n=0
for r in src:
    k=f"{r['gid']}:{r['ply']}"
    if k in done: continue
    if time.time()-t0>budget: break
    b=chess.Board(r['fen'])
    infos=eng.analyse(b, chess.engine.Limit(depth=12), multipv=min(8,b.legal_moves.count()))
    mv=[]
    for i in infos:
        s=i['score'].pov(b.turn).score(mate_score=10000); mv.append((i['pv'][0].uci(), s))
    # played move eval if not in list
    pl=r['played']
    if pl not in [u for u,_ in mv]:
        i=eng.analyse(b, chess.engine.Limit(depth=12), root_moves=[chess.Move.from_uci(pl)])
        mv.append((pl, i['score'].pov(b.turn).score(mate_score=10000)))
    out.write(json.dumps({'k':k,'legal':b.legal_moves.count(),'mv':mv})+'\n'); n+=1
out.close(); eng.quit()
print(shard,'did',n,'total',len(done)+n,'of',len(src))
