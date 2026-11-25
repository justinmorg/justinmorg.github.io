"""Pick and engine-verify 3 lost-game examples per lesson bullet.
Writes examples.json (facts only; text is written by build_study_losses.py)."""
import chess, chess.pgn, chess.engine, json, glob, re, sys, random
import numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/repo/chess/scripts'); sys.path.insert(0, '/home/claude/vis')
from hanging import see, winprob
from emodel import E
SF = '/home/claude/sf/x/usr/games/stockfish'
eng = chess.engine.SimpleEngine.popen_uci(SF); eng.configure({'Threads': 2, 'Hash': 256})
VAL = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3, chess.ROOK:5, chess.QUEEN:9}
CLK = re.compile(r"\[%clk\s+(\d+):(\d+):([\d.]+)\]")

# ---------- games
G = {}
for p in glob.glob('/home/claude/blocks/*.pgn'):
    with open(p) as fh:
        while True:
            g = chess.pgn.read_game(fh)
            if g is None: break
            gid = g.headers['Site'].rsplit('/', 1)[-1]
            b = g.board(); plies = []
            for node in g.mainline():
                mv = node.move; fen = b.fen(); san = b.san(mv); b.push(mv)
                c = CLK.search(node.comment or ''); clk = int(c[1])*3600+int(c[2])*60+float(c[3]) if c else None
                plies.append({'fen': fen, 'uci': mv.uci(), 'san': san, 'clk': clk})
            G[gid] = {'h': dict(g.headers), 'plies': plies, 'final': b.fen(), 'mate': b.is_checkmate()}

def bal(b, me): return sum(v*(len(b.pieces(p, me))-len(b.pieces(p, not me))) for p, v in VAL.items())
def perceived(b, me, last):
    x = bal(b, me)
    if last is not None and b.turn == me and b.is_capture(last) is False:
        pass
    if last is not None and b.turn == me:
        best = 0
        for mv in b.legal_moves:
            if mv.to_square == last.to_square and b.is_capture(mv): best = max(best, see(b, mv))
        x += round(best/100)
    return x

def ana(b, me, depth=18):
    i = eng.analyse(b, chess.engine.Limit(depth=depth))
    s = i['score'].pov(me).score(mate_score=10000)
    pv = i.get('pv', [])[:10]
    bb = b.copy(); sans = []
    for m in pv: sans.append(bb.san(m)); bb.push(m)
    return s, [m.uci() for m in pv], sans

def playout(b, me, last, plies=30, depth=14):
    b = b.copy(); traj = []; sans = []; ucis = []; mate = None
    for k in range(plies+1):
        if b.turn == me: traj.append(perceived(b, me, last))
        if b.is_game_over():
            if b.is_checkmate(): mate = 'me' if b.turn == me else 'opp'
            break
        if k == plies: break
        mv = eng.play(b, chess.engine.Limit(depth=depth)).move
        sans.append(b.san(mv)); ucis.append(mv.uci()); b.push(mv); last = mv
    return traj, sans, ucis, mate

def end_text(gid, me):
    h = G[gid]['h']; n = len(G[gid]['plies']); last_fm = (n+1)//2
    t = h.get('Termination', '')
    if 'Time' in t: how = 'lost on time'
    elif G[gid]['mate']: how = 'checkmated'
    else: how = 'resigned'
    return how, last_fm

def wpct(cp): return winprob(cp)

def base_facts(gid, ply, me_white):
    P = G[gid]['plies']; i = ply-1
    pre = chess.Board(P[i]['fen']); me = pre.turn
    assert me == (chess.WHITE if me_white else chess.BLACK)
    last = chess.Move.from_uci(P[i-1]['uci']) if i >= 1 else None
    mv = chess.Move.from_uci(P[i]['uci'])
    myclk = P[i-2]['clk'] if i >= 2 else 180.0      # my clock before this move
    opclk = P[i-1]['clk'] if i >= 1 else 180.0
    s_best, pv_best, pvs_best = ana(pre, me)
    post = pre.copy(); post.push(mv)
    s_after, pv_rep, pvs_rep = ana(post, me)
    how, last_fm = end_text(gid, me)
    f = {'gid': gid, 'ply': ply, 'white': me == chess.WHITE, 'fullmove': pre.fullmove_number,
         'fen': pre.fen(), 'last': last.uci() if last else None, 'last_san': P[i-1]['san'] if i >= 1 else None,
         'played': mv.uci(), 'played_san': P[i]['san'], 'best': pv_best[0] if pv_best else None,
         'best_san': pvs_best[0] if pvs_best else None, 'best_pv': pvs_best, 'cp_best': s_best, 'cp_after': s_after,
         'reply_pv': pvs_rep, 'reply_pv_uci': pv_rep, 'fen_after': post.fen(),
         'myclk': myclk, 'opclk': opclk, 'pmat': perceived(pre, me, last), 'raw_mat': bal(pre, me),
         'queens_on': bool(pre.pieces(chess.QUEEN, True)) and bool(pre.pieces(chess.QUEEN, False)),
         'my_pieces': {chess.piece_name(p): len(pre.pieces(p, me)) for p in VAL}, 'their_pieces': {chess.piece_name(p): len(pre.pieces(p, not me)) for p in VAL},
         'E_before': float(E(wpct(s_best), max(myclk-P[i]['clk']*0+0, 0) if False else P[i]['clk'] if P[i]['clk'] is not None else myclk, opclk)),
         'E_after': float(E(wpct(s_after), P[i]['clk'] if P[i]['clk'] is not None else myclk, opclk)),
         'how': how, 'last_fm': last_fm, 'date': G[gid]['h'].get('UTCDate', ''), 'opening': G[gid]['h'].get('Opening', ''),
         'result': G[gid]['h'].get('Result')}
    # real continuation: next 6 plies
    f['real_next'] = [P[k]['san'] for k in range(i+1, min(i+7, len(P)))]
    f['real_next_uci'] = [P[k]['uci'] for k in range(i+1, min(i+7, len(P)))]
    # my perceived material at my next turn in the real game
    if i+2 < len(P):
        nb = chess.Board(P[i+2]['fen']); f['real_next_pmat'] = perceived(nb, me, chess.Move.from_uci(P[i+1]['uci']))
        f['fen_real_next'] = P[i+2]['fen']; f['real_reply'] = P[i+1]['uci']; f['real_reply_san'] = P[i+1]['san']
    f['cp_loss'] = s_best - s_after
    f['wp_loss'] = wpct(s_best) - wpct(s_after)
    return f, pre, post, me, last, mv

def solid(f, cp=120, wp=.15):
    return f['played'] != f['best'] and f['cp_loss'] >= cp and f['wp_loss'] >= wp

# ---------- candidate pools
seg = pd.read_parquet('/home/claude/vis/seg.parquet').sort_values(['gid', 'ply'])
seg['next_pmat'] = seg.groupby('gid').pmat.shift(-1); seg['next_ply'] = seg.groupby('gid').ply.shift(-1)
seg['next_cost'] = seg.groupby('gid').cost.shift(-1)
seg['decisive'] = seg.cost == seg.groupby('gid').cost.transform('max')
L = seg[(seg.score == 0) & seg.fullmove.between(10, 50) & (seg.mate_flag == 0)]
paired = pd.read_parquet('/home/claude/vis/paired.parquet')
paired = paired[(paired.score == 0) & paired.fullmove.between(10, 50) & (paired.mate_flag == 0)]
gifts = pd.read_parquet('/home/claude/vis/oppgifts.parquet')
gifts = gifts[(gifts.score == 0) & gifts.fullmove.between(10, 50)]

POOLS = {
 'up12':     L[L.pmat.between(1, 2) & (L.cost >= .2) & (L.wp_before >= .55)],
 'uppiece':  L[(L.pmat >= 3) & (L.cost >= .2) & (L.wp_before >= .6) & (L.next_ply == L.ply+2) & (L.next_pmat <= L.pmat-2)],
 'even':     L[(L.pmat == 0) & L.decisive & (L.cost >= .25) & L.wp_before.between(.4, .65)],
 'queens':   L[(L.queens_on == 1) & L.decisive & (L.cost >= .25) & L.wp_before.between(.4, .8)],
 'lowclock': L[(L.my < 20) & (L.cost >= .25) & (L.wp_before >= .6)],
 'tier1':    paired[(paired.tier.str[0] == '1') & (paired.j == 0) & paired.real_next_drop & paired.pmat.between(-1, 1)],
 'tier2':    paired[(paired.tier.str[0] == '2')],
 'tier3':    paired[(paired.tier.str[0] == '3') & (paired.kind == 'lost material') & paired.j.between(3, 10)],
 'tier4':    paired[(paired.tier.str[0] == '4') & (paired.cost >= .2) & paired.wp_before.between(.35, .85)],
 'giftback': gifts[(gifts.visible == 'nothing to grab') & (gifts.gift >= .2) & (gifts.cost >= .2)],
 'double':   L[(L.cost >= .15) & (L.next_ply == L.ply+2) & (L.next_cost >= .15) & L.wp_before.between(.4, .8)],
}
used = set(); out = {}
rng = random.Random(23)

def check(bul, r):
    gid, ply = r.gid, int(r.ply); me_white = r.side == 'white'
    f, pre, post, me, last, mv = base_facts(gid, ply, me_white)
    if not solid(f): return None
    if bul in ('uppiece', 'tier1'):
        # the real opponent took material right away, and it was a real loss
        if f.get('real_next_pmat') is None or f['real_next_pmat'] > f['pmat']-2: return None
    if bul == 'queens':
        if not f['reply_pv_uci']: return None
        rep = chess.Move.from_uci(f['reply_pv_uci'][0])
        if post.piece_type_at(rep.from_square) != chess.QUEEN: return None
    if bul in ('tier2', 'tier3', 'tier4'):
        tp, sp, up, mp = playout(pre, me, last)          # best line from before the move
        tq, sq, uq, mq = playout(post, me, mv)           # line after the played move
        n = min(len(tq), len(tp)-1); diff = [tq[j]-tp[j+1] for j in range(n)]
        hit = None
        for j, x in enumerate(diff):
            if x <= -2 and all(y <= -1 for y in diff[j:]): hit = j; break
        if mq == 'me' and mp != 'me': return None       # keep mate lines out of these three
        f.update({'best_line': sp, 'played_line': sq, 'traj_best': tp, 'traj_played': tq, 'hit': hit})
        if bul == 'tier2':
            if hit is None or hit > 2: return None
            if not (tp[hit+1]-tp[0] >= 2 and tq[hit]-f['pmat'] > -2): return None
        if bul == 'tier3':
            if hit is None or hit < 3: return None
            if tq[hit]-f['pmat'] > -2: return None
        if bul == 'tier4':
            if hit is not None or min(diff+[0]) <= -2: return None
            if max(abs(t-f['pmat']) for t in tq) >= 2: return None
    if bul == 'giftback':
        P = G[gid]['plies']; i = ply-1
        before_opp = chess.Board(P[i-1]['fen'])                     # their move about to be played
        s0, _, _ = ana(before_opp, me)
        f['cp_before_their_move'] = s0
        f['their_move_san'] = P[i-1]['san']; f['fen_before_their_move'] = P[i-1]['fen']; f['their_prev_move'] = P[i-2]['uci'] if i >= 2 else None
        if f['cp_best'] - s0 < 150 or winprob(f['cp_best']) - winprob(s0) < .15: return None
        grab = max([see(pre, m) for m in pre.legal_moves if pre.is_capture(m)]+[0])
        if grab >= 200: return None
        if f['best'] and pre.is_capture(chess.Move.from_uci(f['best'])) and see(pre, chess.Move.from_uci(f['best'])) >= 200: return None
    if bul == 'double':
        P = G[gid]['plies']; i2 = ply+1
        g2, pre2, post2, _, _, _ = base_facts(gid, ply+2, me_white)
        if not solid(g2): return None
        f['second'] = g2
    return f

TARGET = 3
for bul, pool in POOLS.items():
    ids = list(pool.index); rng.shuffle(ids); got = []
    tried = 0
    for ix in ids:
        r = pool.loc[ix]
        if r.gid in used: continue
        tried += 1
        if tried > 40: break
        try: f = check(bul, r)
        except Exception as e: print('err', bul, r.gid, e); f = None
        if f:
            got.append(f); used.add(r.gid)
            print(bul, r.gid, r.ply, 'ok', flush=True)
        if len(got) == TARGET: break
    out[bul] = got
    print(bul, 'pool', len(pool), 'tried', tried, 'kept', len(got), flush=True)
json.dump(out, open('/home/claude/vis/examples.json', 'w'), indent=1)
eng.quit()
