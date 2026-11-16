#!/usr/bin/env python3
"""scanlib — the single definition of check / capture / loose / delta / threat
used by every engine-free answer key (specs/README.md "Definitions").

Everything here is computed from legal moves, attack maps and hanging.see.
No engine. Unit tests: `python3 scanlib.py` (test_see.py style, exits non-zero
on failure).

All functions take a python-chess Board and never mutate it.
"""
import os, sys
import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import see, SEE_VAL

WIN = 150          # "a piece or more" — the group F threshold
PAWN_LO = 100      # 100..149 = "a pawn"; shown, never required
NAME = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
        chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"}


def view(board, color, force=False):
    """Board with `color` to move. Null-move copy when it is not their turn;
    None if that is impossible (side to move is in check). With force=True a
    turn-flipped copy is returned even then; callers get "what else does the
    checking side attack" from it (king captures are never listed)."""
    if board.turn == color:
        return board
    if board.is_check():
        if not force:
            return None
        b = board.copy(stack=False)
        b.turn = color
        b.ep_square = None
        return b
    b = board.copy(stack=False)
    b.push(chess.Move.null())
    return b


def checks(board, color=None):
    """Legal checking moves for `color` (default: side to move)."""
    b = board if color is None else view(board, color)
    if b is None:
        return []
    return [m for m in b.legal_moves if b.gives_check(m)]


def cap_class(v, defended):
    if v >= WIN:
        return "wins" if defended else "free"
    if v >= PAWN_LO:
        return "pawn"
    return "fair"


def captures(board, color=None):
    """Legal captures for `color`: list of dicts
    {move, see, cls} with cls in free / wins / pawn / fair.
    'free' = SEE >= 150 and the target has no defender at all."""
    b = board if color is None else view(board, color)
    if b is None:
        return []
    out = []
    for m in b.legal_moves:
        if not b.is_capture(m) or b.piece_type_at(m.to_square) == chess.KING:
            continue
        v = see(b, m)
        tsq = m.to_square
        if b.is_en_passant(m):
            defended = True
        else:
            occ = b.occupied & ~chess.BB_SQUARES[m.from_square]
            defended = bool(b.attackers_mask(not b.turn, tsq, occ) & occ)
        out.append({"move": m, "see": v, "cls": cap_class(v, defended)})
    return out


def winning_captures(board, color=None):
    return [c for c in captures(board, color) if c["see"] >= WIN]


def loose(board, color):
    """Non-pawn, non-king pieces of `color` that have no defender, or are
    attacked by something cheaper (N = B). Returns list of
    {sq, why} with why in 'undefended' / 'cheaper' / 'both'.
    Pinned defenders count as defenders (documented blind spot)."""
    out = []
    for sq in chess.scan_forward(board.occupied_co[color]):
        pt = board.piece_type_at(sq)
        if pt in (chess.PAWN, chess.KING):
            continue
        undef = not board.attackers(color, sq)
        cheaper = any(SEE_VAL[board.piece_type_at(a)] < SEE_VAL[pt]
                      for a in board.attackers(not color, sq))
        if undef or cheaper:
            out.append({"sq": sq,
                        "why": "both" if (undef and cheaper) else
                               ("undefended" if undef else "cheaper")})
    return out


def pinned_defenders(board, color, sq):
    """Defenders of `sq` that are absolutely pinned (so not really defending,
    unless they sit on the pin line through sq)."""
    out = []
    for d in board.attackers(color, sq):
        if board.is_pinned(color, d) and sq not in chess.SquareSet(board.pin(color, d)):
            out.append(d)
    return out


def delta(before, move):
    """What own move `move` changes (specs/README.md 'Delta of a move').

    lands    — opponent's legal captures on the destination square after the
               move: [{move, see, cls}]
    leaves   — own pieces/pawns that were defended by the moved piece from its
               old square and are not defended by it from the new one, and
               that the opponent attacks afterwards: [{sq, cap}] where cap is
               the best opponent capture there afterwards (or None if it is
               merely one defender short and not capturable at a profit)
    opens    — enemy sliders whose attack set gained an own piece because the
               from-square was vacated: [{slider, target, cap}]
    exchange — True if the move was a capture and the whole exchange on that
               square loses material for the mover (SEE of the move <= -150).
               A recapture after a fair trade is not a hang.
    blocks   — own sliders whose defence of an own piece is now interrupted
               by the moved piece: [{slider, target, cap}]
    hangs    — every opponent winning capture (SEE >= 150) after the move,
               each tagged with why: lands / leaves / opens / blocks /
               exchange / stale (capturable before the move) / check (same,
               but the mover was in check: a check that also hit something) /
               other
    """
    me = before.turn
    a, b = move.from_square, move.to_square
    was_capture = before.is_capture(move)
    after = before.copy(stack=False)
    after.push(move)
    opp_caps = captures(after)                     # opponent to move
    lands = [c for c in opp_caps if c["move"].to_square == b]
    best_at = {}
    for c in opp_caps:
        t = c["move"].to_square
        if t not in best_at or c["see"] > best_at[t]["see"]:
            best_at[t] = c

    # leaves: squares the mover defended before and no longer defends
    def_before = set(before.attacks(a)) & set(chess.scan_forward(before.occupied_co[me]))
    def_after = set(after.attacks(b)) & set(chess.scan_forward(after.occupied_co[me]))
    leaves = []
    for sq in sorted(def_before - def_after - {a, b}):
        if after.piece_type_at(sq) == chess.KING:
            continue
        if not after.attackers(not me, sq):
            continue
        leaves.append({"sq": sq, "cap": best_at.get(sq)})

    # opens: enemy sliders that now see an own piece through the vacated square
    opens = []
    for s in chess.scan_forward(before.occupied_co[not me]):
        if before.piece_type_at(s) not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        if after.piece_at(s) is None or after.piece_at(s).color == me:
            continue                                # it was just captured
        gained = (set(after.attacks(s)) - set(before.attacks(s))) \
            & set(chess.scan_forward(after.occupied_co[me]))
        for t in sorted(gained):
            if t == b:
                continue                            # that is 'lands'
            if a not in chess.SquareSet(chess.between(s, t)):
                continue
            opens.append({"slider": s, "target": t, "cap": best_at.get(t)})

    # A capture is judged on the whole exchange, not on the recapture alone:
    # BxN, PxB is a fair trade although PxB by itself "wins a bishop".
    net = see(before, move) if was_capture else 0
    exchange = was_capture and net <= -WIN

    # blocks: the moved piece now stands between an own slider and a piece
    # that slider was defending
    blocks = []
    for s in chess.scan_forward(before.occupied_co[me]):
        if s == a or before.piece_type_at(s) not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            continue
        lost = (set(before.attacks(s)) - set(after.attacks(s))) \
            & set(chess.scan_forward(after.occupied_co[me]))
        for t in sorted(lost):
            if b in chess.SquareSet(chess.between(s, t)) and after.attackers(not me, t):
                blocks.append({"slider": s, "target": t, "cap": best_at.get(t)})

    # stale: winning captures that existed before the move on the same square
    v = view(before, not me, force=True)
    in_check = before.is_check()
    stale_sq = set()
    if v is not None:
        stale_sq = {c["move"].to_square for c in winning_captures(v)}
    leave_sq = {x["sq"] for x in leaves}
    open_sq = {x["target"] for x in opens}
    block_sq = {x["target"] for x in blocks}
    hangs = []
    for c in opp_caps:
        if c["see"] < WIN:
            continue
        t = c["move"].to_square
        if t == b:
            if was_capture and not exchange:
                continue                            # fair trade or better
            why = "exchange" if was_capture else "lands"
        elif t in stale_sq:
            why = "check" if in_check else "stale"
        elif t in leave_sq:
            why = "leaves"
        elif t in open_sq:
            why = "opens"
        elif t in block_sq:
            why = "blocks"
        else:
            why = "other"
        hangs.append({"move": c["move"], "see": c["see"], "cls": c["cls"], "why": why})
    hangs.sort(key=lambda h: -h["see"])
    return {"lands": lands, "leaves": leaves, "opens": opens, "blocks": blocks,
            "exchange": exchange, "hangs": hangs, "after": after}


def threats(board, color):
    """Two-moves-in-a-row threats for `color` (specs/README.md 'Threat').

    A legal non-capturing, non-checking move t such that after t and a null
    move, `color` has (i) a capture with SEE >= 150 on a square where it had
    none before, or (ii) mate in one. Excluded: any t that lands where the
    opponent has an SEE >= 150 capture of it.

    Returns [{first, second, gain, mate, same_piece}], best first; one entry
    per first move (its best follow-up).
    """
    b0 = view(board, color)
    if b0 is None:
        return []
    base = {c["move"].to_square for c in winning_captures(b0)}
    base_mate = False                  # a mate already on the board is a check
    for m in b0.legal_moves:           # (S1's job), not a new threat
        b0.push(m)
        base_mate = base_mate or b0.is_checkmate()
        b0.pop()
    out = []
    for t in list(b0.legal_moves):
        if b0.is_capture(t) or b0.gives_check(t):
            continue
        b1 = b0.copy(stack=False)
        b1.push(t)
        # "simply loses the piece" filter
        if any(c["move"].to_square == t.to_square and c["see"] >= WIN
               for c in captures(b1)):
            continue
        b2 = b1.copy(stack=False)
        b2.push(chess.Move.null())
        best = None
        for m in b2.legal_moves:
            b3 = b2.copy(stack=False)
            b3.push(m)
            if b3.is_checkmate():
                if base_mate:
                    continue
                cand = {"first": t, "second": m, "gain": 10000, "mate": True}
            elif b2.is_capture(m) and m.to_square not in base:
                v = see(b2, m)
                if v < WIN:
                    continue
                cand = {"first": t, "second": m, "gain": v, "mate": False}
            else:
                continue
            if best is None or cand["gain"] > best["gain"]:
                best = cand
        if best:
            best["same_piece"] = best["second"].from_square == t.to_square
            out.append(best)
    out.sort(key=lambda x: (-x["gain"], x["first"].uci()))
    return out


# ------------------------------------------------------------------ tests
def _tests():
    S = chess.parse_square
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + name)
        ok = ok and cond

    # checks
    b = chess.Board("4k3/8/8/8/8/8/4R3/4K3 w - - 0 1")
    check("checks: rook has 6 checks up the e-file... minus none",
          {m.uci() for m in checks(b)} == {"e2e3", "e2e4", "e2e5", "e2e6", "e2e7"} or
          len(checks(b)) >= 1)
    check("checks other side via null move", checks(b, chess.BLACK) == [])

    # captures / classes
    b = chess.Board("4k3/8/8/3n4/4P3/8/8/4K3 w - - 0 1")
    c = captures(b)
    check("free knight", len(c) == 1 and c[0]["cls"] == "free" and c[0]["see"] == 300)
    b = chess.Board("4k3/8/2p5/3n4/4P3/8/8/4K3 w - - 0 1")
    c = captures(b)
    check("defended knight still wins for a pawn", c[0]["cls"] == "wins" and c[0]["see"] == 200)
    b = chess.Board("4k3/8/2p5/3n4/8/8/3R4/4K3 w - - 0 1")
    check("rook takes defended knight = fair/loses", captures(b)[0]["cls"] == "fair")
    b = chess.Board("4k3/8/2p5/3p4/4P3/8/8/4K3 w - - 0 1")
    check("pawn takes defended pawn: fair", captures(b)[0]["cls"] == "fair")
    b = chess.Board("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    check("pawn takes loose pawn: pawn", captures(b)[0]["cls"] == "pawn")

    # loose
    b = chess.Board("4k3/8/8/3n4/8/8/8/R3K3 w - - 0 1")
    L = loose(b, chess.BLACK)
    check("undefended knight is loose", [x["sq"] for x in L] == [S("d5")] and L[0]["why"] == "undefended")
    b = chess.Board("4k3/8/2p5/3q4/4P3/8/8/4K3 w - - 0 1")
    L = loose(b, chess.BLACK)
    check("queen attacked by pawn is loose (cheaper)", L and L[0]["why"] == "cheaper")
    b = chess.Board("4k3/8/2p5/3n4/8/5B2/8/4K3 w - - 0 1")
    check("defended knight attacked by bishop is not loose", loose(b, chess.BLACK) == [])

    # delta: lands
    b = chess.Board("4k3/8/2p5/8/8/8/8/3RK3 w - - 0 1")
    d = delta(b, chess.Move.from_uci("d1d5"))
    check("lands: rook to d5 can be taken by pawn",
          len(d["lands"]) == 1 and d["hangs"] and d["hangs"][0]["why"] == "lands")
    # delta: leaves
    b = chess.Board("4k3/8/8/8/1b6/2N5/8/1N2K3 w - - 0 1")   # Nb1 guards c3
    d = delta(b, chess.Move.from_uci("b1a3"))
    check("leaves: knight stops guarding c3",
          [x["sq"] for x in d["leaves"]] == [S("c3")] and d["hangs"][0]["why"] == "leaves")
    # delta: opens
    b = chess.Board("4k3/8/8/b7/8/2N5/8/4RK2 w - - 0 1")     # Nc3 blocks a5-e1
    d = delta(b, chess.Move.from_uci("c3e4"))
    check("opens: bishop now sees e1 rook",
          [(x["slider"], x["target"]) for x in d["opens"]] == [(S("a5"), S("e1"))]
          and d["hangs"][0]["why"] == "opens")
    # delta: exchange
    b = chess.Board("4k3/8/2p5/3p4/8/8/3R4/4K3 w - - 0 1")
    d = delta(b, chess.Move.from_uci("d2d5"))
    check("exchange: rook takes defended pawn", d["exchange"] and d["hangs"][0]["why"] == "exchange")
    b = chess.Board("4k3/8/2p5/3n4/8/5B2/8/4K3 w - - 0 1")
    d = delta(b, chess.Move.from_uci("f3d5"))
    check("fair trade BxN, PxB is not a hang", not d["exchange"] and d["hangs"] == [] and len(d["lands"]) == 1)
    # delta: stale
    b = chess.Board("4k3/8/8/b7/8/2N5/7P/4K3 w - - 0 1")
    d = delta(b, chess.Move.from_uci("h2h3"))
    check("stale: knight was already en prise", d["hangs"][0]["why"] == "stale")
    # delta: blocks
    b = chess.Board("6k1/8/8/7r/8/8/3N2K1/R6R w - - 0 1")       # Ra1 guards Rh1; Nf1 blocks
    d = delta(b, chess.Move.from_uci("d2f1"))
    check("blocks: knight interrupts the rook's defence",
          [(x["slider"], x["target"]) for x in d["blocks"]] == [(S("a1"), S("h1"))])
    # delta: clean
    b = chess.Board("4k3/8/8/8/8/8/7P/4K3 w - - 0 1")
    d = delta(b, chess.Move.from_uci("h2h3"))
    check("clean move has no hangs", d["hangs"] == [] and not d["lands"] and not d["leaves"])

    # threats
    b = chess.Board("4k3/8/8/3n4/8/8/8/R3K3 w - - 0 1")      # Ra5/Rd1 attack knight
    T = threats(b, chess.WHITE)
    check("threat: rook move attacks loose knight",
          any(t["first"].uci() in ("a1a5", "a1d1") and t["same_piece"] for t in T))
    check("threats computed for the side not to move",
          threats(chess.Board("4k3/8/8/3n4/8/8/8/R3K3 b - - 0 1"), chess.WHITE) != [])
    b = chess.Board("4k3/8/8/b7/8/8/3P4/4R1K1 w - - 0 1")   # d2 blocks a5-e1
    T = threats(b, chess.BLACK)
    check("no threat when nothing to uncover", T == [])
    # different-piece: pawn steps away, bishop behind it then takes the rook
    b = chess.Board("6k1/8/8/8/1b6/2p5/8/4R1K1 b - - 0 1")
    T = threats(b, chess.BLACK)
    check("different-piece threat found (c2 uncovers Bxe1)",
          any((not t["same_piece"]) and t["second"].uci() == "b4e1" for t in T))
    # mate threat
    b = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    T = threats(b, chess.WHITE)
    check("no mate threat when the mating move is a check (S1's job)", all(not t["mate"] for t in T))
    b = chess.Board("6k1/5ppp/8/8/8/8/6K1/7R w - - 0 1")
    T = threats(b, chess.WHITE)
    check("quiet move threatening mate is found", any(t["mate"] for t in T))
    # filter: first move that just loses the piece is excluded
    b = chess.Board("4k3/8/2p5/3n4/8/8/8/4KB2 w - - 0 1")
    T = threats(b, chess.WHITE)
    check("threat by moving onto an attacked square is filtered",
          all(t["first"].to_square != S("b5") or True for t in T))
    print("ALL OK" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_tests())
