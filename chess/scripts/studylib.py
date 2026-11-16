#!/usr/bin/env python3
"""studylib — corpus loader for the chess-study builders.

Loads every depth-12 annotated Lichess block (plus data/pending/) into plain
dicts, 3+2 / 5+0 only, and caches the parse. Selection helper only: nothing
loaded here is a verdict shown to the player except where a builder says so.

    games = studylib.load()          # list of dicts, oldest first
    g = {gid, date, tc, me (chess.WHITE/BLACK), result ('1-0'..), score (1/.5/0
         from my side), opening, eco, block, moves [uci], evals [cp white POV
         after each ply or None], clocks [sec or None], termination}
"""
import os, re, gzip, glob, io, pickle, sys
import chess, chess.pgn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import parse_eval

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
USER = "jamorgan"
TCS = ("180+2", "300+0")
CLK = re.compile(r"\[%clk (\d+):(\d+):(\d+)")
CACHE = os.environ.get("STUDY_CACHE", "/tmp/study_corpus.pkl")


def files():
    fs = sorted(glob.glob(os.path.join(DATA, "jamorgan_blitz_*_analyzed.pgn.gz")))
    fs += sorted(glob.glob(os.path.join(DATA, "pending", "*.pgn.gz")))
    return fs


def load(refresh=False):
    if not refresh and os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    out, seen = [], set()
    for f in files():
        block = os.path.basename(f).replace("jamorgan_blitz_", "").replace("_analyzed.pgn.gz", "")
        if "pending" in f:
            block = "pending"
        txt = io.StringIO(gzip.open(f, "rt", encoding="utf-8").read())
        while True:
            game = chess.pgn.read_game(txt)
            if game is None:
                break
            h = game.headers
            if h.get("TimeControl") not in TCS or h.get("Variant", "Standard") != "Standard":
                continue
            if "FEN" in h:
                continue
            gid = h.get("GameId") or h.get("Site", "").rsplit("/", 1)[-1]
            if gid in seen:
                continue
            if h.get("White") == USER:
                me = chess.WHITE
            elif h.get("Black") == USER:
                me = chess.BLACK
            else:
                continue
            seen.add(gid)
            moves, evals, clocks = [], [], []
            node = game
            while node.variations:
                node = node.variations[0]
                white_moved = node.parent.board().turn == chess.WHITE
                moves.append(node.move.uci())
                evals.append(parse_eval(node.comment, white_moved))
                m = CLK.search(node.comment or "")
                clocks.append(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None)
            res = h.get("Result")
            sc = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(res)
            if sc is None or len(moves) < 10:
                continue
            if me == chess.BLACK:
                sc = 1.0 - sc
            out.append({"gid": gid, "date": h.get("UTCDate", h.get("Date")), "tc": h["TimeControl"],
                        "me": me, "result": res, "score": sc, "opening": h.get("Opening", ""),
                        "eco": h.get("ECO", ""), "block": block, "moves": moves, "evals": evals,
                        "clocks": clocks, "termination": h.get("Termination", ""),
                        "my_elo": h.get("WhiteElo" if me else "BlackElo"),
                        "opp_elo": h.get("BlackElo" if me else "WhiteElo")})
    out.sort(key=lambda g: (g["date"], g["gid"]))
    pickle.dump(out, open(CACHE, "wb"))
    return out


def drilled_gids():
    """Game ids that already appear on the chess-drills pages (P / F / R / fresh)."""
    ids = set()
    for p in ("../../chess-drills/index.html", "../../chess-drills/fresh/index.html"):
        p = os.path.join(HERE, p)
        if os.path.exists(p):
            ids |= set(re.findall(r"lichess\.org/([A-Za-z0-9]{8})(?:[#/\"?]|$)", open(p, encoding="utf-8").read()))
    return ids


def my_pov(cp, me):
    return None if cp is None else (cp if me == chess.WHITE else -cp)


if __name__ == "__main__":
    gs = load(refresh=True)
    from collections import Counter
    print(len(gs), "games"); print(Counter(g["block"] for g in gs)); print(Counter(g["tc"] for g in gs))
    print("drilled gids:", len(drilled_gids()))
