#!/usr/bin/env python3
"""
matedanger.py — flag positions where a wrong move would hand the opponent a
forced mate (bucket M2 in buckets_prespec.md).

Usage:
    python3 matedanger.py FEATURES_DIR OUT.csv [--workers 2] [--depth 12]

FEATURES_DIR must come from `features.py ... --emit-fens all`. One output row
per own move whose position is not already a mate score:

    gid, ply, in_check, a_null, b_m1, c_check

  a_null   not in check; after a null move, Stockfish (depth 12) reports a
           forced mate for the opponent — a standing mate threat
  b_m1     some legal move lets the opponent mate in one (board logic only)
  c_check  in check; some legal move leads to a position where Stockfish
           reports a forced mate for the opponent

Resumable: rows already in OUT.csv are skipped. Engine path from
STOCKFISH_PATH, default /home/claude/sf/x/usr/games/stockfish (see README,
"Stockfish in a fresh sandbox"). Use the same Stockfish 16 the corpus used.
"""
import argparse
import csv
import logging
import os
import sys
from multiprocessing import Pool

import chess
import chess.engine
import pandas as pd

logging.getLogger("chess.engine").setLevel(logging.ERROR)  # null-move history notice
SF = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
MATE_CP = 10000
_eng = None
DEPTH = 12


def _init(depth):
    global _eng, DEPTH
    DEPTH = depth
    _eng = chess.engine.SimpleEngine.popen_uci(SF)
    _eng.configure({"Threads": 1, "Hash": 64})


def opp_has_mate(board):
    """Side to move in `board` is the opponent; does the engine see mate for them?"""
    sc = _eng.analyse(board, chess.engine.Limit(depth=DEPTH))["score"].pov(board.turn)
    return sc.is_mate() and sc.mate() > 0


def allows_mate_in_one(board):
    """Opponent to move: is there a checkmating reply?"""
    for mv in board.legal_moves:
        board.push(mv)
        mate = board.is_checkmate()
        board.pop()
        if mate:
            return True
    return False


def probe(item):
    gid, ply, fen = item
    b = chess.Board(fen)
    chk = b.is_check()
    a = c = 0
    if not chk:
        nb = b.copy(stack=False)
        nb.push(chess.Move.null())
        a = int(opp_has_mate(nb))
    bm1 = 0
    for mv in list(b.legal_moves):
        b.push(mv)
        if not bm1 and allows_mate_in_one(b):
            bm1 = 1
        if chk and not c and not b.is_checkmate() and opp_has_mate(b):
            c = 1
        b.pop()
        if bm1 and (c or not chk):
            break
    return gid, ply, int(chk), a, bm1, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("features")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--depth", type=int, default=12)
    a = ap.parse_args()

    m = pd.read_csv(os.path.join(a.features, "moves.csv.gz"),
                    dtype={"block": str, "gid": str},
                    usecols=["gid", "ply", "cp_before"])
    f = pd.read_csv(os.path.join(a.features, "fens.csv.gz"),
                    dtype={"block": str, "gid": str}, usecols=["gid", "ply", "fen"])
    m = m.merge(f, on=["gid", "ply"], how="left")
    if m.fen.isna().any():
        sys.exit("missing FENs — run features.py with --emit-fens all")
    m = m[m.cp_before.abs() < MATE_CP]

    done = set()
    if os.path.exists(a.out):
        d = pd.read_csv(a.out, dtype={"gid": str})
        done = set(zip(d.gid, d.ply))
    todo = [(g, p, fe) for g, p, fe in m[["gid", "ply", "fen"]].itertuples(index=False)
            if (g, p) not in done]
    print(f"{len(m)} positions, {len(done)} done, {len(todo)} to go", flush=True)

    new = not os.path.exists(a.out)
    with open(a.out, "a", newline="") as fh, \
            Pool(a.workers, initializer=_init, initargs=(a.depth,)) as pool:
        w = csv.writer(fh)
        if new:
            w.writerow(["gid", "ply", "in_check", "a_null", "b_m1", "c_check"])
        for i, row in enumerate(pool.imap_unordered(probe, todo, chunksize=64), 1):
            w.writerow(row)
            if i % 5000 == 0:
                fh.flush()
                print(f"  {i}/{len(todo)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
