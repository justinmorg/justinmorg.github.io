#!/usr/bin/env python3
"""review/deep.py — deeper looks at each review game's deciding move.

    STOCKFISH_PATH=... python3 chess/scripts/review/deep.py

Run after evaluate.py. For every game with a deciding move (keys.analyse):
  - the position before it: MultiPV 4 at depth 20 -> cache[fen4]["mpv"] =
    [[uci, cp_white, pv_ucis[:12]]]   (the move card's accepted answers)
  - the position after it (opponent to move): depth 20 -> cache[fen4]["ref"] =
    [cp_white, pv_ucis[:12]]   (how the move is punished)
Same cache file as evaluate.py.
"""
import os, sys, json
import chess, chess.engine

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keys  # noqa: E402
from evaluate import CACHE, PICK, SF, cp_of  # noqa: E402


def main():
    games = json.load(open(PICK))
    c = json.load(open(CACHE))
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    eng.configure({"Threads": 2, "Hash": 256})
    for g in games:
        r = keys.analyse(g, c)
        if not r["key"]:
            print(g["gid"], "no key", flush=True)
            continue
        B = keys.boards(g)
        pre, post = B[r["key"] - 1], B[r["key"]]
        e = c[keys.fen4(pre)]
        if "mpv" not in e:
            info = eng.analyse(pre, chess.engine.Limit(depth=20), multipv=4)
            e["mpv"] = [[x["pv"][0].uci(), cp_of(x["score"]), [m.uci() for m in x["pv"][:12]]] for x in info]
        e2 = c[keys.fen4(post)]
        if "ref" not in e2 and not post.is_game_over():
            x = eng.analyse(post, chess.engine.Limit(depth=20))
            e2["ref"] = [cp_of(x["score"]), [m.uci() for m in x["pv"][:12]]]
        json.dump(c, open(CACHE, "w"), sort_keys=True, separators=(",", ":"))
        print(g["gid"], "key ply", r["key"], flush=True)
    eng.quit()


if __name__ == "__main__":
    main()
