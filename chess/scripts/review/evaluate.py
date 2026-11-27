#!/usr/bin/env python3
"""review/evaluate.py — pick the 30 games for the game-review deck and evaluate every position.

    STOCKFISH_PATH=... python3 chess/scripts/review/evaluate.py

Selection: the 30 most recent losses in the group F treatment block
(jamorgan_blitz_2026_fblock_analyzed.pgn.gz, 3+2 / 5+0 via studylib), ordered by
UTCDate + UTCTime, skipping any game already used by another chess-study deck
(card keys carry the game id). Then a fresh Stockfish search at depth 16 on every
position of those games (before each ply, and the final position). The deeper
looks at each game's deciding move are in deep.py. Resumable cache:
chess/study/review_engine.json (fen4 -> {d16: cp_white, ...}).
The depth-12 corpus evals are not used for anything shown on a card.
"""
import os, sys, json, gzip, io, glob
import chess, chess.pgn, chess.engine

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import studylib  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
CACHE = os.path.join(ROOT, "study", "review_engine.json")
PICK = os.path.join(ROOT, "study", "review_pick.json")
SF = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
N = 30


def fen4(b):
    return " ".join(b.fen().split()[:4])


def cp_of(score):
    s = score.white()
    if s.is_mate():
        m = s.mate()
        return 10000 - abs(m) if m > 0 else -10000 + abs(m)
    return s.score()


def used_gids():
    used = set()
    for p in glob.glob(os.path.join(ROOT, "..", "chess-study", "data", "*.json")):
        if os.path.basename(p).startswith(("review", "index", "test")):
            continue
        d = json.load(open(p, encoding="utf-8"))
        for c in d.get("cards", []):
            parts = c["k"].split("-")
            if len(parts) >= 3:
                used.add("-".join(parts[1:-1]))
    return used


def times():
    t = {}
    f = os.path.join(ROOT, "data", "jamorgan_blitz_2026_fblock_analyzed.pgn.gz")
    txt = io.StringIO(gzip.open(f, "rt", encoding="utf-8").read())
    while True:
        h = chess.pgn.read_headers(txt)
        if h is None:
            break
        gid = h.get("GameId") or h.get("Site", "").rsplit("/", 1)[-1]
        t[gid] = (h.get("UTCDate", ""), h.get("UTCTime", ""), h.get("White"), h.get("Black"),
                  h.get("WhiteElo"), h.get("BlackElo"))
    return t


def pick():
    G = studylib.load()
    T = times()
    used = used_gids()
    L = [g for g in G if g["block"] == "2026_fblock" and g["score"] == 0 and g["gid"] not in used]
    L.sort(key=lambda g: T[g["gid"]][:2])
    sel = L[-N:]
    out = []
    for g in sel:
        d, tm, w, b, we, be = T[g["gid"]]
        me = g["me"]
        out.append({"gid": g["gid"], "date": d, "time": tm, "tc": g["tc"], "me": "w" if me else "b",
                    "opp": b if me else w, "opp_elo": be if me else we, "my_elo": we if me else be,
                    "opening": g["opening"], "termination": g["termination"], "result": g["result"],
                    "moves": g["moves"], "clocks": g["clocks"]})
    return out


def main():
    games = pick()
    json.dump(games, open(PICK, "w"), indent=0)
    c = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    eng.configure({"Threads": 2, "Hash": 256})
    done = 0
    for gi, g in enumerate(games):
        b = chess.Board()
        me = chess.WHITE if g["me"] == "w" else chess.BLACK
        plies = g["moves"]
        for i in range(len(plies) + 1):
            k = fen4(b)
            e = c.setdefault(k, {})
            if b.is_game_over():
                if "d16" not in e:
                    e["d16"] = (-10000 if b.turn == chess.WHITE else 10000) if b.is_checkmate() else 0
            else:
                if "d16" not in e:
                    e["d16"] = cp_of(eng.analyse(b, chess.engine.Limit(depth=16))["score"])
            if i < len(plies):
                b.push_uci(plies[i])
            done += 1
            if done % 50 == 0:
                json.dump(c, open(CACHE, "w"), sort_keys=True, separators=(",", ":"))
        print("game %d/%d %s" % (gi + 1, len(games), g["gid"]), flush=True)
    json.dump(c, open(CACHE, "w"), sort_keys=True, separators=(",", ":"))
    eng.quit()


if __name__ == "__main__":
    main()
