"""Engine self-play from a position, recording my perceived material each time I'm to move.
usage: playout.py JOBS.csv OUT.jsonl SHARD NSHARDS   (resumable)"""
import sys, json, os, chess, chess.engine, pandas as pd
sys.path.insert(0, '/home/claude/repo/chess/scripts')
from hanging import see
VAL = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3, chess.ROOK:5, chess.QUEEN:9}
def bal(b, me):
    t = sum(v*(len(b.pieces(p, me))-len(b.pieces(p, not me))) for p, v in VAL.items()); return t
def perceived(b, me, last):
    x = bal(b, me)
    if last is not None and b.turn == me:
        best = 0
        for mv in b.legal_moves:
            if mv.to_square == last.to_square and b.is_capture(mv): best = max(best, see(b, mv))
        x += round(best/100)
    return x
jobs, out, sh, ns = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
J = pd.read_csv(jobs, dtype={'gid': str}); J = J[J.index % ns == sh]
done = set()
if os.path.exists(out):
    for l in open(out): done.add(json.loads(l)['key'])
e = chess.engine.SimpleEngine.popen_uci('/home/claude/sf/x/usr/games/stockfish'); e.configure({'Threads': 1, 'Hash': 64})
DEPTH, PLIES = 10, 30
with open(out, 'a') as fo:
    for r in J.itertuples():
        if r.key in done: continue
        b = chess.Board(r.fen); me = b.turn
        last = None
        if r.mode == 'post':
            mv = chess.Move.from_uci(r.uci); b.push(mv); last = mv
        traj = []; mate = None
        for k in range(PLIES+1):
            if b.turn == me: traj.append(perceived(b, me, last))
            if b.is_game_over():
                if b.is_checkmate(): mate = 'me' if b.turn == me else 'opp'   # 'me' = I got mated
                break
            if k == PLIES: break
            mv = e.play(b, chess.engine.Limit(depth=DEPTH)).move; b.push(mv); last = mv
        fo.write(json.dumps({'key': r.key, 'traj': traj, 'mate': mate})+'\n'); fo.flush()
e.quit()
