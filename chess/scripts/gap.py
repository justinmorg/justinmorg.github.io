"""How much does the 'immediate capture >=150' rule miss?

Run 2026-09-03 to settle the scope question - see the README's "Scope: what
'hanging material' does and does not cover". Result: the rule catches 196 of
the 5,529 eligible moves; a further 761 drop >10 win-percent with no capture
available, of which ~22% lose a piece by force (classify_gap.py). Conclusion
was to KEEP the narrow scope and treat the metric as a lower bound.


Walk the corpus. For every eligible winning-middlegame own move, classify by
what the CURRENT rule says, and separately by what actually happened.
"""
import json,sys,math
import chess, chess.pgn
sys.path.insert(0,'/home/claude/justinmorg.github.io/chess/scripts')
from hanging import see, threat_after, parse_eval, winprob, npm, USER
FLOOR=0.05
rows=[]
fh=open('/home/claude/corpus.pgn')
while True:
    g=chess.pgn.read_game(fh)
    if g is None: break
    hw,hb=g.headers.get("White",""),g.headers.get("Black","")
    me=chess.WHITE if USER==hw else chess.BLACK if USER==hb else None
    if me is None: continue
    gid=g.headers.get("GameId","")
    b=g.board(); prev=0; ply=0; node=g
    while node.variations:
        node=node.variations[0]; mv=node.move; mover=b.turn; ply+=1
        e=parse_eval(node.comment, mover==chess.WHITE)
        if mover==me:
            cp_b = prev if me==chess.WHITE else -prev
            cp_a_w = e if e is not None else prev
            cp_a = cp_a_w if me==chess.WHITE else -cp_a_w
            if b.fullmove_number>12 and npm(b,"light")>14 and cp_b>=150:
                after=b.copy(stack=False); after.push(mv)
                sv,_=threat_after(b,mv,after)
                we=winprob(cp_b)-winprob(cp_a)
                rows.append({"gid":gid,"ply":ply,"fen":b.fen(),"m":mv.uci(),
                             "sv":sv,"we":round(we,3),"cb":cp_b,"ca":cp_a})
        else:
            pass
        b.push(mv); prev = e if e is not None else prev
json.dump(rows,open('/home/claude/eligible.json','w'))
n=len(rows)
caught=[r for r in rows if r['sv']>=150 and r['we']>FLOOR]
missed=[r for r in rows if r['sv']<150 and r['we']>0.10]
pawn  =[r for r in rows if 100<=r['sv']<150 and r['we']>FLOOR]
print(f"eligible winning-middlegame moves: {n}")
print(f"  caught by current rule (SEE>=150 & we>{FLOOR}): {len(caught)}  ({100*len(caught)/n:.2f}%)")
print(f"  pawn-only capture available & we>{FLOOR}     : {len(pawn)}  ({100*len(pawn)/n:.2f}%)")
print(f"  NO immediate capture, but we>0.10           : {len(missed)}  ({100*len(missed)/n:.2f}%)")
