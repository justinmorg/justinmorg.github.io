#!/usr/bin/env python3
"""studyauthor — a small DSL for hand-authored lesson and drill cards.

A card is a list of S (show) and Q (question) items played on one running
board. Every SAN is checked for legality; every `tb=` expectation and every
Q on a position with <= 7 men is checked against the Lichess tablebase
(tbprobe, cached in chess/study/tb_cache.json); every `ev=` expectation and
every Q with more men is checked against Stockfish (enginecheck, cached in
chess/study/engine_cache.json). A card whose claims do not verify does not
build.

Text conventions: `Re4` in backticks renders as a move; blank line = new
paragraph; plain HTML is allowed.
"""
import re
import chess
import tbprobe
from studycards import mv, after, SQ

OUTCOME = {"draw": "Then it is only a draw.", "loss": "That loses.", "win": "That even wins for the other side.",
           "unknown": "That lets the result slip."}


def fmt(text):
    text = re.sub(r"`([^`]+)`", lambda m: mv(m.group(1)), text.strip())
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "".join(p if p.startswith("<") else "<p>%s</p>" % p for p in paras)


def inline(text):
    return re.sub(r"`([^`]+)`", lambda m: mv(m.group(1)), text.strip())


def parse_arrows(s):
    return [[a.split(":")[0], (a.split(":") + ["g"])[1]] for a in s.split()] if s else []


def parse_marks(s):
    return [[a.split(":")[0], (a.split(":") + ["y"])[1]] for a in s.split()] if s else []


class S(object):
    def __init__(self, text, play="", fen=None, arrows="", marks="", tb=None, ev=None, flip=None, nolast=False):
        self.__dict__.update(locals())


class Q(object):
    """Move question. `method` = SAN(s) accepted as the answer (first is the
    lesson move). On <= 7 men: every other tablebase-keeping move becomes a
    neutral 'also works, find the method move' nudge, and every remaining
    legal move gets its tablebase outcome as feedback. `bad` overrides the
    feedback for specific SANs. On more men: `also` lists further acceptable
    SANs (engine-checked), `bad` gives specific refutations."""
    def __init__(self, ask, method, note="", play="", fen=None, hint=None, bad=None, also=None,
                 text="", arrows="", marks="", strict=False, accept_all=False, tol=70, flip=None):
        self.__dict__.update(locals())
        if isinstance(self.method, str):
            self.method = [self.method]


class C(object):
    """Choice question on the current position."""
    def __init__(self, ask, options, answer, explain="", play="", fen=None, text="", arrows="", marks="",
                 rarrows="", rmarks="", tb=None, flip=None):
        self.__dict__.update(locals())


def men(board):
    return chess.popcount(board.occupied)


def build(key, title, sub, flip, items, engine=None, links=None):
    """-> card dict. `engine` is an enginecheck.Engine (needed only for >7-men checks)."""
    board, last, steps = None, None, []
    for it in items:
        if it.fen:
            board, last = chess.Board(it.fen), None
        assert board is not None or isinstance(it, S), "%s: no position yet" % key
        if it.play:
            for san in it.play.split():
                try:
                    m = board.parse_san(san)
                except Exception as e:
                    raise AssertionError("%s: illegal %s in %s (%s)" % (key, san, board.fen(), e))
                board.push(m)
                last = m
        base = {}
        if board is not None:
            base = {"fen": board.fen()}
            if last is not None and not getattr(it, "nolast", False):
                base["last"] = last.uci()
        if getattr(it, "flip", None) is not None:
            base["flip"] = it.flip
        if it.arrows:
            base["arrows"] = parse_arrows(it.arrows)
        if it.marks:
            base["marks"] = parse_marks(it.marks)
        if isinstance(it, S):
            if it.tb:
                got = tbprobe.result_white(board.fen())
                assert got == it.tb, "%s: tablebase says %s, card says %s at %s" % (key, got, it.tb, board.fen())
            if it.ev is not None:
                engine.expect(board.fen(), it.ev, key)
            st = dict(base, type="show", text=fmt(it.text))
            steps.append(st)
        elif isinstance(it, C):
            if it.tb:
                got = tbprobe.result_white(board.fen())
                assert got == it.tb, "%s: tablebase says %s, card says %s at %s" % (key, got, it.tb, board.fen())
            st = dict(base, type="choice", ask=inline(it.ask), options=it.options, answer=it.answer,
                      explain=inline(it.explain))
            if it.text:
                st["text"] = fmt(it.text)
            if it.rarrows:
                st["rarrows"] = parse_arrows(it.rarrows)
            if it.rmarks:
                st["rmarks"] = parse_marks(it.rmarks)
            steps.append(st)
        else:
            st = dict(base, type="move", ask=inline(it.ask), accept={}, alt={}, bad={})
            if it.text:
                st["text"] = fmt(it.text)
            if it.hint:
                st["hint"] = inline(it.hint)
            meth = [board.parse_san(s) for s in it.method]
            badn = {board.parse_san(s).uci(): inline(t) for s, t in (it.bad or {}).items()}
            if men(board) <= 7:
                goal, keep, others = tbprobe.keeping_moves(board.fen())
                for m in meth:
                    assert m.uci() in keep, "%s: %s does not keep the %s at %s" % (key, board.san(m), goal, board.fen())
                word = "wins" if goal == "win" else "draws"
                for u in keep:
                    m = chess.Move.from_uci(u)
                    if m in meth or it.accept_all:
                        note = inline(it.note) if m == meth[0] else (
                            "That %s too. The lesson move is %s. %s" % (word, mv(board.san(meth[0])), inline(it.note)))
                        st["accept"][u] = {"san": board.san(m), "fen": after(board, m).fen(), "note": note}
                    elif not it.strict:
                        st["alt"][u] = "%s also %s here (the tablebase agrees), but it is not the method this card is practising. Look for the other move." % (mv(board.san(m)), word)
                    else:
                        st["alt"][u] = "%s also %s, but there is a cleaner move." % (mv(board.san(m)), word)
                for u, oc in others.items():
                    m = chess.Move.from_uci(u)
                    st["bad"][u] = badn.get(u) or ("%s: %s" % (mv(board.san(m)), OUTCOME.get(oc, OUTCOME["unknown"])))
            else:
                ok = list(meth) + [board.parse_san(s) for s in (it.also or [])]
                if engine is not None:
                    engine.accept_check(board.fen(), [m.uci() for m in ok], key, tol=it.tol)
                for m in ok:
                    note = inline(it.note) if m == meth[0] else (
                        "That is fine too. The repertoire move here is %s. %s" % (mv(board.san(meth[0])), inline(it.note)))
                    st["accept"][m.uci()] = {"san": board.san(m), "fen": after(board, m).fen(), "note": note}
                st["bad"] = badn
            st["main"] = meth[0].uci()
            for k in ("alt", "bad"):
                if not st[k]:
                    del st[k]
            steps.append(st)
            board.push(meth[0])
            last = meth[0]
    card = {"k": key, "t": title, "sub": sub, "flip": flip, "steps": steps}
    if links:
        card["links"] = links
    return card


def number_line(board, sans):
    """'1.Ke4 Kd6 2.Kf5' from a board and a SAN list (numbers restart at 1)."""
    out, n, white = [], 1, board.turn == chess.WHITE
    for i, s in enumerate(sans):
        if white:
            out.append("%d.%s" % (n, s))
        else:
            out.append(("%d...%s" % (n, s)) if i == 0 else s)
            n += 1
        white = not white
    return " ".join(out)
