"""How quick material losses happen: classify the mechanism from the position after the error.
usage: mech.py SHARD NSHARDS"""
import sys, json, os, chess, chess.engine, pandas as pd
sys.path.insert(0, '/home/claude/repo/chess/scripts'); from hanging import see
VAL = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3, chess.ROOK:5, chess.QUEEN:9, chess.KING:0}
def bal(b, me): return sum(v*(len(b.pieces(p, me))-len(b.pieces(p, not me))) for p, v in VAL.items())
def resolved(b, me):
    x = bal(b, me)
    if b.is_checkmate(): return x + (-40 if b.turn == me else 40)
    best = max([see(b, m) for m in b.legal_moves if b.is_capture(m)] + [0]) / 100
    return x + (best if b.turn == me else -best)
def xcount(b, color, sq):
    """attackers of sq by color, counting pieces lined up behind them (batteries / x-rays)"""
    bb = b.copy(stack=False); n = 0; kinds = []
    for _ in range(8):
        a = list(bb.attackers(color, sq))
        if not a: break
        n += len(a); kinds += [chess.piece_name(bb.piece_type_at(s)) for s in a]
        for s in a: bb.remove_piece_at(s)
    return n, kinds
def en_prise(b, me):
    """my pieces the side to move (them) can win by a capture with SEE > 0: {sq: see}"""
    out = {}
    for m in b.legal_moves:
        if b.is_capture(m) and b.color_at(m.to_square) == me:
            s = see(b, m)
            if s > 0: out[m.to_square] = max(out.get(m.to_square, 0), s)
    return out
sh, ns = int(sys.argv[1]), int(sys.argv[2])
J = pd.read_csv('mechjobs.csv', dtype={'gid': str}); J = J[J.index % ns == sh]
out = f'mech{sh}.jsonl'; done = set()
if os.path.exists(out): done = {json.loads(l)['k'] for l in open(out)}
e = chess.engine.SimpleEngine.popen_uci('/home/claude/sf/x/usr/games/stockfish'); e.configure({'Threads': 1, 'Hash': 64})
with open(out, 'a') as fo:
    for r in J.itertuples():
        k = f'{r.gid}:{r.ply}'
        if k in done: continue
        pre = chess.Board(r.fen); me = pre.turn; mv = chess.Move.from_uci(r.uci)
        last = pre.peek() if pre.move_stack else None
        m0 = r.pmat
        b = pre.copy(); b.push(mv)
        info = e.analyse(b, chess.engine.Limit(depth=13))
        pv = info.get('pv', [])[:5]           # their move, mine, theirs, mine, theirs
        c = b.copy()
        for m in pv: c.push(m)
        loss = m0 - resolved(c, me)
        res = {'k': k, 'loss6': loss, 'pv': [x.uci() for x in pv]}
        if pv:
            ep_before = en_prise(b, me)
            first = pv[0]
            res['first_cap'] = b.is_capture(first); res['first_check'] = b.gives_check(first)
            res['first_piece'] = chess.piece_name(b.piece_type_at(first.from_square))
            # pieces of mine en prise right after my move
            res['ep_after_my_move'] = {chess.square_name(s): v for s, v in ep_before.items()}
            res['moved_to'] = chess.square_name(mv.to_square)
            # was each en-prise square already en prise before my move (i.e. a standing threat)?
            # compare against the position before my move with them to move (null move)
            nb = pre.copy()
            if not nb.is_check():
                nb.push(chess.Move.null()); epn = en_prise(nb, me)
                res['ep_before_my_move'] = {chess.square_name(s): v for s, v in epn.items()}
            tgt = first.to_square if b.is_capture(first) else None
            if tgt is not None and tgt in ep_before:
                att = list(b.attackers(not me, tgt)); dfn = list(b.attackers(me, tgt))
                res['tgt'] = chess.square_name(tgt); res['tgt_piece'] = chess.piece_name(b.piece_type_at(tgt))
                res['n_att'] = len(att); res['n_def'] = len(dfn)
                res['nx_att'], _ = xcount(b, not me, tgt); res['nx_def'], res['defx_kinds'] = xcount(b, me, tgt)
                res['min_att'] = min(VAL[b.piece_type_at(s)] or 100 for s in att)
                res['def_kinds'] = [chess.piece_name(b.piece_type_at(s)) for s in dfn]
                # did my move create this (piece moved there, or a defender left / a line opened)?
                pb = pre
                res['tgt_was_mine_before'] = pb.color_at(tgt) == me and pb.piece_type_at(tgt) == b.piece_type_at(tgt)
                res['def_before'] = len(pb.attackers(me, tgt)) if res['tgt_was_mine_before'] else None
                res['att_before'] = len(pb.attackers(not me, tgt)) if res['tgt_was_mine_before'] else None
                if res['tgt_was_mine_before']:
                    res['nx_def_before'] = xcount(pb, me, tgt)[0]; res['nx_att_before'] = xcount(pb, not me, tgt)[0]
            else:
                # quiet / check / non-winning capture first: what does it set up?
                b2 = b.copy(); b2.push(first)
                ep2 = en_prise(b2, me) if b2.turn != me else {}
                # with me to move after their move, look at threats by a null-move swap
                if not b2.is_check():
                    b3 = b2.copy(); b3.push(chess.Move.null()); ep2 = en_prise(b3, me)
                else:
                    ep2 = {}
                new = {s: v for s, v in ep2.items() if s not in ep_before}
                mover_sq = first.to_square
                disc = []; byself = []
                for s in new:
                    atts = [a for a in b2.attackers(not me, s)]
                    if any(a != mover_sq for a in atts) and mover_sq not in atts: disc.append(s)
                    elif mover_sq in atts: byself.append(s)
                # discovered: a piece other than the mover now attacks something of mine it did not attack before
                disc_any = False; disc_targets = []
                mine_valuable = [s for s in chess.SquareSet(b2.occupied_co[me]) if b2.piece_type_at(s) != chess.PAWN]
                for a in chess.SquareSet(b2.occupied_co[not me]):
                    if a == mover_sq: continue
                    before = b.attacks(a) if b.color_at(a) == (not me) else chess.SquareSet()
                    for s in mine_valuable:
                        if s in b2.attacks(a) and s not in before:
                            disc_any = True; disc_targets.append(chess.square_name(s))
                res['setup_disc_targets'] = disc_targets
                res['setup_new_targets'] = len(new); res['setup_disc'] = disc_any
                res['setup_mover_targets'] = len(byself) + (1 if b2.is_check() and b2.king(me) in [s for s in b2.attacks(mover_sq)] else 0)
                res['setup_check'] = b2.is_check()
        fo.write(json.dumps(res) + '\n'); fo.flush()
e.quit()
