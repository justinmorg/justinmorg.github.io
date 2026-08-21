#!/usr/bin/env python3
"""Extract middlegame positions where jamorgan was >= +150cp and material hung."""
import chess, chess.pgn, re, math, json, sys

USER = "jamorgan"
SEE_VAL = {chess.PAWN:100, chess.KNIGHT:300, chess.BISHOP:300,
           chess.ROOK:500, chess.QUEEN:900, chess.KING:10000}
MATE_CP = 10000

# ---------------------------------------------------------------- SEE
def see(board, move):
    """Static exchange evaluation of `move` in centipawns, from mover's POV."""
    to_sq = move.to_square
    if board.is_en_passant(move):
        cap_val = SEE_VAL[chess.PAWN]
    else:
        p = board.piece_type_at(to_sq)
        if p is None:
            return 0
        cap_val = SEE_VAL[p]

    occupied = board.occupied & ~chess.BB_SQUARES[move.from_square]
    if board.is_en_passant(move):
        ep_sq = to_sq + (-8 if board.turn == chess.WHITE else 8)
        occupied &= ~chess.BB_SQUARES[ep_sq]

    on_square = SEE_VAL[board.piece_type_at(move.from_square)]
    if move.promotion:
        on_square = SEE_VAL[move.promotion]
        cap_val += SEE_VAL[move.promotion] - SEE_VAL[chess.PAWN]

    gains = [cap_val]
    side = not board.turn
    d = 0
    while True:
        att = board.attackers_mask(side, to_sq, occupied) & occupied
        if not att:
            break
        best_sq, best_val = None, 10**9
        for sq in chess.scan_forward(att):
            v = SEE_VAL[board.piece_type_at(sq)]
            if v < best_val:
                best_val, best_sq = v, sq
        # a king may not capture into a still-defended square
        if best_val == SEE_VAL[chess.KING]:
            rest = occupied & ~chess.BB_SQUARES[best_sq]
            if board.attackers_mask(not side, to_sq, rest) & rest:
                break
        d += 1
        gains.append(on_square - gains[d-1])
        occupied &= ~chess.BB_SQUARES[best_sq]
        on_square = best_val
        side = not side
    while d > 0:
        gains[d-1] = -max(-gains[d-1], gains[d])
        d -= 1
    return gains[0]


def best_capture_see(board):
    """Max SEE over the side-to-move's legal captures. Returns (see, move)."""
    best, bm = 0, None
    for m in board.legal_moves:
        if board.is_capture(m):
            s = see(board, m)
            if s > best:
                best, bm = s, m
    return best, bm


def threat_after(before, move, after):
    """Material the opponent can win after `move`, correctly netted.

    For the square `move` captured on, the whole swap (my capture, their
    recapture, my re-recapture...) is already summarised by see(before, move),
    so an even trade nets 0 rather than looking like a hung piece. Every other
    square is scored by the opponent's own SEE.
    """
    my_cap_sq = move.to_square if before.is_capture(move) else None
    my_swap = see(before, move) if my_cap_sq is not None else None
    best, bm = 0, None
    for m in after.legal_moves:
        if not after.is_capture(m):
            continue
        if my_cap_sq is not None and m.to_square == my_cap_sq:
            val = -my_swap                    # net loss over the full exchange
        else:
            val = see(after, m)
        if val > best:
            best, bm = val, m
    return best, bm


# ---------------------------------------------------------------- eval
EVAL_RE = re.compile(r"\[%eval ([^\]]+)\]")

def parse_eval(comment, mover_is_white):
    """-> centipawns from WHITE's POV, or None."""
    m = EVAL_RE.search(comment or "")
    if not m:
        return None
    tok = m.group(1).strip()
    if tok.startswith("#"):
        n = tok[1:]
        if n in ("0", "-0"):          # mate just delivered by the mover
            return MATE_CP if mover_is_white else -MATE_CP
        v = int(n)
        return MATE_CP if v > 0 else -MATE_CP
    return int(round(float(tok) * 100))


def winprob(cp):
    """Lichess logistic, cp clamped to +/-1000 as Lichess does."""
    if cp >= MATE_CP:  return 1.0
    if cp <= -MATE_CP: return 0.0
    cp = max(-1000, min(1000, cp))
    return 1.0 / (1.0 + math.exp(-0.00368208 * cp))


# ---------------------------------------------------------------- phase
def npm(board, scale):
    """Non-pawn material, both sides."""
    if scale == "light":   v = {chess.KNIGHT:1, chess.BISHOP:1, chess.ROOK:2, chess.QUEEN:4}
    else:                  v = {chess.KNIGHT:3, chess.BISHOP:3, chess.ROOK:5, chess.QUEEN:9}
    t = 0
    for pt, val in v.items():
        t += val * (len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK)))
    return t


# ---------------------------------------------------------------- scan
def scan(path, scale):
    rows = []
    stats = {"games":0, "user_moves":0, "in_check":0}
    with open(path) as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            stats["games"] += 1
            hw, hb = game.headers.get("White",""), game.headers.get("Black","")
            if USER == hw:   me = chess.WHITE
            elif USER == hb: me = chess.BLACK
            else:            continue

            board = game.board()
            prev_eval = 0          # eval of the start position, white POV
            ply = 0
            node = game
            while node.variations:
                node = node.variations[0]
                move = node.move
                mover = board.turn
                ply += 1

                if mover == me:
                    stats["user_moves"] += 1
                    cp_before_me = prev_eval if me == chess.WHITE else -prev_eval
                    if (board.fullmove_number > 12
                            and npm(board, scale) > 14
                            and cp_before_me >= 150):
                        row = probe(board, move, node, me, cp_before_me,
                                    game, ply, stats)
                        if row:
                            rows.append(row)

                e = parse_eval(node.comment, mover == chess.WHITE)
                board.push(move)
                prev_eval = e if e is not None else prev_eval
            # end game
    return rows, stats


def probe(board, move, node, me, cp_before_me, game, ply, stats):
    # threats already on the board before my move (null-move probe)
    in_check = board.is_check()
    if in_check:
        stats["in_check"] += 1
    # Null-move probe: what could they take if I did nothing? This is valid even
    # when I'm in check (a piece can be hanging *and* my king attacked), but the
    # resulting position is technically illegal, so ignore "captures" of my king.
    nb = board.copy(stack=False)
    nb.push(chess.Move.null())
    my_king = board.king(board.turn)
    before_see = 0
    for m in nb.legal_moves:
        if not nb.is_capture(m) or m.to_square == my_king:
            continue
        before_see = max(before_see, see(nb, m))

    after = board.copy(stack=False)
    after.push(move)
    after_see, after_mv = threat_after(board, move, after)

    if after_see < 150:
        return None                       # nothing hanging after my move

    label = "missed their threat" if before_see >= 150 else "hung it myself"

    cp_after_w = parse_eval(node.comment, me == chess.WHITE)
    if cp_after_w is None:
        return None
    cp_after_me = cp_after_w if me == chess.WHITE else -cp_after_w

    wp_b, wp_a = winprob(cp_before_me), winprob(cp_after_me)

    return {
        "fen": board.fen(),
        "side": "white" if me == chess.WHITE else "black",
        "label": label,
        "in_check": in_check,
        "move_played": board.san(move),
        "their_capture": after.san(after_mv),
        "see_after": after_see,
        "see_before": before_see,
        "cp_before": cp_before_me,
        "cp_after": cp_after_me,
        "wp_error": wp_b - wp_a,
        "fullmove": board.fullmove_number,
        "ply": ply,
        "gid": game.headers.get("GameId",""),
        "opp": (game.headers.get("Black") if me == chess.WHITE
                else game.headers.get("White")),
        "opp_elo": (game.headers.get("BlackElo") if me == chess.WHITE
                    else game.headers.get("WhiteElo")),
        "date": game.headers.get("UTCDate","").replace(".", "-"),
        "opening": game.headers.get("Opening",""),
        "result": game.headers.get("Result",""),
        "tc": game.headers.get("TimeControl",""),
    }


if __name__ == "__main__":
    scale = sys.argv[2] if len(sys.argv) > 2 else "light"
    rows, stats = scan(sys.argv[1], scale)
    rows.sort(key=lambda r: -r["wp_error"])
    json.dump(rows, open(f"/home/claude/hits_{scale}.json","w"), indent=1)
    from collections import Counter
    c = Counter(r["label"] for r in rows)
    print(f"scale={scale}  games={stats['games']}  user_moves={stats['user_moves']}")
    print(f"  total hits      : {len(rows)}")
    print(f"  missed their threat: {c['missed their threat']}")
    print(f"  hung it myself     : {c['hung it myself']}")
    print(f"  (in check at decision point: {sum(1 for r in rows if r['in_check'])})")
    for th in (0.20, 0.25, 0.30):
        print(f"  wp_error >= {th:.2f}: {sum(1 for r in rows if r['wp_error']>=th)}")
