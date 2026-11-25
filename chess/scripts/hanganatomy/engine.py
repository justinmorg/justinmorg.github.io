#!/usr/bin/env python3
"""Step 2: depth-18 re-search of every hit (resumable, parallel).

Per hit, three searches, all scores from jamorgan's POV in cp (mate = +-10000):
  P0  the position before his move    -> best move, score, PV
  P1  after the move he played        -> score, PV (opponent's best line)
  P2  after the move + the flagged capture (`their_capture`) -> score, PV
P1 vs P2 says whether the flagged capture is actually the opponent's right
reply; the PVs feed the material bookkeeping in analyze.py.

    python3 engine.py hits.json out.jsonl [workers]
"""
import json, os, sys, time
from multiprocessing import Pool
import chess, chess.engine

SF = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
DEPTH = 18
PV_MAX = 16
_eng = None


def key(h):
    return f"{h['gid']}-{h['ply']}"


def init():
    global _eng
    _eng = chess.engine.SimpleEngine.popen_uci(SF)
    _eng.configure({"Threads": 1, "Hash": 128})


def search(board, me):
    info = _eng.analyse(board, chess.engine.Limit(depth=DEPTH))
    sc = info["score"].pov(me).score(mate_score=10000)
    pv = [m.uci() for m in info.get("pv", [])[:PV_MAX]]
    return sc, pv


def work(h):
    b = chess.Board(h["fen"])
    me = b.turn
    rec = {"key": key(h)}
    rec["s0"], rec["pv0"] = search(b, me)
    played = b.parse_san(h["move_played"])
    b.push(played)
    rec["s1"], rec["pv1"] = search(b, me)
    cap = b.parse_san(h["their_capture"])
    rec["cap_uci"] = cap.uci()
    b.push(cap)
    rec["s2"], rec["pv2"] = search(b, me)
    return rec


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    hits = json.load(open(src))
    done = set()
    if os.path.exists(dst):
        done = {json.loads(l)["key"] for l in open(dst)}
    todo = [h for h in hits if key(h) not in done]
    print(f"{len(hits)} hits, {len(done)} done, {len(todo)} to do", flush=True)
    t0 = time.time()
    with Pool(workers, initializer=init) as pool, open(dst, "a") as fh:
        for i, rec in enumerate(pool.imap_unordered(work, todo), 1):
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            if i % 25 == 0:
                el = time.time() - t0
                print(f"  {i}/{len(todo)}  {el:.0f}s  eta {el/i*(len(todo)-i):.0f}s",
                      flush=True)
    print("done", flush=True)
