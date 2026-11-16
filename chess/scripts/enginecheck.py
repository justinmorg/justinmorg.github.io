#!/usr/bin/env python3
"""enginecheck — Stockfish checks for authored cards, with a committed cache.

Used at build time only, to refuse cards whose claims do not hold up:
  expect(fen, (lo, hi))        eval in pawns, White's point of view
  accept_check(fen, ucis, tol) each accepted move within `tol` cp of the best
  best(fen, n)                 top-n moves [(uci, cp_white, pv_ucis)]
  move_eval(fen, uci)          eval after forcing one move

Cache: chess/study/engine_cache.json, keyed by position + depth + query, so a
rebuild without an engine reproduces the same decks. Engine path from
STOCKFISH_PATH (default: the Stockfish 17.1 binary used on 2026-11-16).
"""
import os, json
import chess, chess.engine

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "study", "engine_cache.json")
DEFAULT = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/sf17/stockfish/stockfish-ubuntu-x86-64-avx2")


def _cp(score, white=True):
    s = score.white()
    if s.is_mate():
        return 10000 if s.mate() > 0 else -10000
    return s.score()


class Engine(object):
    def __init__(self, depth=20, path=DEFAULT):
        self.depth, self.path, self.eng = depth, path, None
        self.c = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
        self.dirty = 0

    def _engine(self):
        if self.eng is None:
            self.eng = chess.engine.SimpleEngine.popen_uci(self.path)
            self.eng.configure({"Threads": 2, "Hash": 256})
        return self.eng

    def save(self):
        if self.dirty:
            json.dump(self.c, open(CACHE, "w"), sort_keys=True, separators=(",", ":"))
            self.dirty = 0

    def close(self):
        self.save()
        if self.eng is not None:
            self.eng.quit()
            self.eng = None

    def _key(self, fen, tag, depth):
        return "%s|d%d|%s" % (" ".join(fen.split()[:4]), depth, tag)

    def best(self, fen, n=3, depth=None):
        depth = depth or self.depth
        k = self._key(fen, "mpv%d" % n, depth)
        if k not in self.c:
            b = chess.Board(fen)
            info = self._engine().analyse(b, chess.engine.Limit(depth=depth), multipv=n)
            self.c[k] = [[i["pv"][0].uci(), _cp(i["score"]), [m.uci() for m in i["pv"][:8]]] for i in info if "pv" in i]
            self.dirty += 1
            if self.dirty % 20 == 0:
                self.save()
        return [tuple(x) for x in self.c[k]]

    def move_eval(self, fen, uci, depth=None):
        depth = depth or self.depth
        k = self._key(fen, "mv" + uci, depth)
        if k not in self.c:
            b = chess.Board(fen)
            info = self._engine().analyse(b, chess.engine.Limit(depth=depth), root_moves=[chess.Move.from_uci(uci)])
            self.c[k] = [_cp(info["score"]), [m.uci() for m in info.get("pv", [])[:8]]]
            self.dirty += 1
            if self.dirty % 20 == 0:
                self.save()
        return tuple(self.c[k])

    def expect(self, fen, rng, key):
        lo, hi = rng
        cp = self.best(fen, 1)[0][1]
        assert lo * 100 <= cp <= hi * 100, "%s: engine says %+.2f, card expects %s..%s at %s" % (key, cp / 100.0, lo, hi, fen)

    def accept_check(self, fen, ucis, key, tol=70):
        white = fen.split()[1] == "w"
        top = self.best(fen, 1)[0][1]
        for u in ucis:
            cp = self.move_eval(fen, u)[0]
            loss = (top - cp) if white else (cp - top)
            assert loss <= tol, "%s: %s loses %d cp against the engine's best at %s" % (
                key, chess.Board(fen).san(chess.Move.from_uci(u)), loss, fen)

    def mover_cp(self, fen, cp):
        return cp if fen.split()[1] == "w" else -cp
