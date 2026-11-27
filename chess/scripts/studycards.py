#!/usr/bin/env python3
"""studycards — shared helpers for the chess-study deck builders.

Deck JSON schema (consumed by chess-study/index.html):

  deck  = {id, title, cards: [card]}
  card  = {k, t, sub?, flip?, links?: [[label, url]], steps: [step]}
  step  = {type, fen, last?, arrows?: [[uci, colour]], marks?: [[sq, colour]],
           text?: html, next?: label, ...}
    type "show"    read-only screen
    type "tap"     ask, key: [sq], none?: label, rtext?, rarrows?, rmarks?
    type "move"    ask, accept: {uci: {san, fen, note?, arrows?}}, main: uci,
                   bad?: {uci: html}, hint?, wrong?, none?: label,
                   noneOk?: bool, noneText?
    type "choice"  ask, options: [label], answer: index, explain?, rarrows?,
                   rmarks?, rfen?, rlast?
    type "playout" play: [[label, url]]
    type "verify"  ask, options?: [label]   (unscored; test suite "did that work?", review-deck gut call)
    type "game"    step through a whole game: fen = start, first: 'w'|'b', fm0: first
                   fullmove, me: 'w'|'b', base: start clock (s), plies: [[san, fen_after,
                   uci, clock_after_s|None]], ask, key: 1-based ply of the deciding
                   own move (0 = no move, "none" button is the answer), also?: [ply],
                   none?: label, rok?/ralso?/rno?/rtext?: html
  colours: g green, r red, b blue, y gold, k ink.

Card keys are stable ids: `{deck}-{gid}-{ply}` for positions from games,
`{deck}-{slug}` for authored cards. localStorage object: `study.v1`.
"""
import os, json, hashlib
import chess
import scanlib
from hanging import SEE_VAL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "chess-study", "data")
NAME = scanlib.NAME
SQ = chess.square_name


def mv(san):
    return '<span class="mv">%s</span>' % san


def pname(board, sq, the=True):
    p = board.piece_at(sq)
    return ("the " if the else "") + "%s on %s" % (NAME[p.piece_type], SQ(sq))


def worth(v):
    """SEE gain in plain words (pawn 1, knight or bishop 3, rook 5, queen 9)."""
    table = {100: "a pawn", 300: "a piece", 500: "a rook", 900: "a queen"}
    if v >= 10000:
        return "mate"
    if v in table:
        return table[v]
    return "%g points" % (v / 100.0)


def gain_text(board, m, v):
    """What a winning capture nets, in words: 'the queen for a rook'."""
    if board.is_en_passant(m):
        return "a pawn"
    tv = SEE_VAL[board.piece_type_at(m.to_square)]
    av = SEE_VAL[board.piece_type_at(m.from_square)]
    tn = NAME[board.piece_type_at(m.to_square)]
    an = NAME[board.piece_type_at(m.from_square)]
    if v == tv:
        return "the %s" % tn
    if v == tv - av and v > 0:
        return "the %s for %s %s" % (tn, "a", an)
    return "%s (pawn 1, piece 3, rook 5, queen 9)" % worth(v)


def cap_text(board, c, who="they"):
    """'Bxf6 takes the knight on f6 for nothing' — c from scanlib.captures on `board`."""
    m = c["move"]
    san = board.san(m)
    tgt = m.to_square
    v = c["see"]
    if board.is_en_passant(m):
        what = "a pawn en passant"
    else:
        what = pname(board, tgt)
    if c["cls"] == "free":
        tail = "for nothing"
    elif c["cls"] == "wins":
        g = gain_text(board, m, v)
        tail = "and wins it outright, since the defence does not hold" if g == "the %s" % NAME[board.piece_type_at(tgt)] \
            else "and comes out ahead: %s" % g
    elif c["cls"] == "pawn":
        tail = "and wins a pawn"
    elif v < 0:
        tail = "but it is defended, so the capture would lose material"
    else:
        tail = "but that is an even trade"
    return "%s takes %s %s" % (mv(san), what, tail)


def after(board, move):
    b = board.copy(stack=False)
    b.push(move)
    return b


def gsub(r_or_g, me, fm, extra=None):
    bits = ["move %d" % fm, "you're %s" % ("White" if me else "Black")]
    if extra:
        bits.append(extra)
    return " &middot; ".join(bits)


def fam(opening):
    o = opening or ""
    for key, name in (("London", "London"), ("Caro-Kann", "Caro-Kann"), ("Englund", "Englund"),
                      ("Queen's Pawn", "Queen's Pawn"), ("Indian", "Indian setup")):
        if key in o:
            return name
    return o.split(":")[0][:28] if o else ""


def game_link(gid, ply, me):
    return ["The real game", "https://lichess.org/%s%s#%d" % (gid, "" if me else "/black", ply)]


def write_deck(deck):
    os.makedirs(OUT, exist_ok=True)
    keys = [c["k"] for c in deck["cards"]]
    assert len(keys) == len(set(keys)), "duplicate card keys in " + deck["id"]
    for c in deck["cards"]:
        for key in [x for x in c if x.startswith("_")]:
            del c[key]
        for st in c["steps"]:
            validate_step(st, c["k"])
    p = os.path.join(OUT, deck["id"] + ".json")
    json.dump(deck, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return {"id": deck["id"], "keys": keys, "bytes": os.path.getsize(p)}


def validate_step(st, k):
    assert st["type"] in ("show", "tap", "move", "choice", "playout", "verify", "game"), k
    if "fen" in st:
        chess.Board(st["fen"])                       # parses
    for a in st.get("arrows", []) + st.get("rarrows", []):
        assert len(a[0]) >= 4 and a[1] in "grbyk", (k, a)
    if st["type"] == "tap":
        assert isinstance(st["key"], list) and st["ask"], k
    if st["type"] == "move":
        b = chess.Board(st["fen"])
        if not st.get("noneOk"):
            assert st["main"] in st["accept"], k
        for u, acc in st["accept"].items():
            m = chess.Move.from_uci(u)
            if st.get("turn_flip"):
                continue
            assert m in b.legal_moves, (k, u, st["fen"])
            assert chess.Board(acc["fen"]).board_fen() == after(b, m).board_fen(), (k, u)
    if st["type"] == "choice":
        assert 0 <= st["answer"] < len(st["options"]), k
    if st["type"] == "game":
        b = chess.Board(st["fen"])
        assert ("w" if b.turn else "b") == st["first"] and b.fullmove_number == st["fm0"], k
        for i, (san, fen, uci, _c) in enumerate(st["plies"]):
            m = chess.Move.from_uci(uci)
            assert b.san(m) == san, (k, i, san)
            b.push(m)
            assert b.board_fen() == chess.Board(fen).board_fen(), (k, i)
        mine = lambda j: ((j - 1) % 2 == 0) == (st["first"] == st["me"])
        assert st["key"] == 0 and st.get("none") or (1 <= st["key"] <= len(st["plies"]) and mine(st["key"])), k
        assert all(mine(j) and j != st["key"] for j in st.get("also", [])), k
