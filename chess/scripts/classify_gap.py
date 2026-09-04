"""Of the moves the current rule misses, how many lose MATERIAL by force?

For each sampled position: after my move, take the engine's principal
variation at depth 18 and compare my material balance at the start of that
line with the balance at the end. A drop of >=150 means the opponent wins a
piece by force within the line - a tactic I could in principle have seen by
scanning. No drop means the eval fell for positional reasons.
"""
import json,os,sys,random,time
import chess, chess.engine
SF="/home/claude/sf/x/usr/games/stockfish"
V={chess.PAWN:100,chess.KNIGHT:300,chess.BISHOP:300,chess.ROOK:500,chess.QUEEN:900}
def bal(b,me): return sum(V[p]*(len(b.pieces(p,me))-len(b.pieces(p,not me))) for p in V)
rows=json.load(open('/home/claude/eligible.json'))
arm=sys.argv[1]; N=int(sys.argv[2]); OUT=f'/home/claude/cls_{arm}.jsonl'
if arm=='miss':  pool=[r for r in rows if r['sv']<150 and r['we']>0.10]
elif arm=='pawn':pool=[r for r in rows if 100<=r['sv']<150 and r['we']>0.05]
random.Random(23).shuffle(pool); pool=pool[:N]
done=set()
if os.path.exists(OUT):
    for l in open(OUT): done.add(json.loads(l)['fen']+json.loads(l)['m'])
pool=[r for r in pool if r['fen']+r['m'] not in done]
eng=chess.engine.SimpleEngine.popen_uci(SF); t0=time.time()
with open(OUT,'a') as fh:
    for r in pool:
        b=chess.Board(r['fen']); me=b.turn; b.push_uci(r['m'])
        b0=bal(b,me)
        info=eng.analyse(b,chess.engine.Limit(depth=18))
        pv=info['pv'][:6]
        opp_first = b.san(pv[0]) if pv else ""
        opp_is_capture = b.is_capture(pv[0]) if pv else False
        for m in pv: b.push(m)
        r2=dict(r); r2.update({"d_mat":bal(b,me)-b0,"opp1":opp_first,
                               "opp1_cap":int(opp_is_capture),
                               "fa":info['score'].pov(me).score(mate_score=10000)})
        fh.write(json.dumps(r2)+"\n"); fh.flush()
eng.quit(); print(f"{len(pool)} in {time.time()-t0:.0f}s")
