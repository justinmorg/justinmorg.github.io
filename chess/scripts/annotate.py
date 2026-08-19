#!/usr/bin/env python3
"""
annotate.py — add [%eval] comments to a Lichess PGN using local Stockfish.

Matches the canonical format of jamorgan_blitz_2026_analyzed.pgn:
    { [%eval 0.38] [%clk 0:03:00] }
Mate scores render as #N / #-N (White's perspective), #0 for delivered mate.
Existing [%clk] comments are preserved; existing [%eval] comments are
replaced so the whole corpus is uniform depth-12 local analysis.

Usage: python3 annotate.py IN.pgn OUT.pgn [--depth 12] [--workers 4]
"""
import argparse
import io
import multiprocessing as mp
import os
import re
import sys

import chess
import chess.engine
import chess.pgn

ENGINE = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
CLK_RE = re.compile(r"\[%clk\s+([^\]]+)\]")


def fmt_eval(score):
    """chess.engine.PovScore (White POV) -> Lichess-style eval string."""
    if score.is_mate():
        return "#%d" % score.mate()
    cp = score.score()
    return ("%.2f" % (cp / 100.0)).rstrip("0").rstrip(".")


def annotate_game(game_text, depth):
    game = chess.pgn.read_game(io.StringIO(game_text))
    if game is None:
        return game_text
    board = game.board()
    engine = chess.engine.SimpleEngine.popen_uci(ENGINE)
    try:
        engine.configure({"Threads": 1, "Hash": 64})
        for node in game.mainline():
            board.push(node.move)
            if board.is_checkmate():
                ev = "#0"
            elif board.is_stalemate() or board.is_insufficient_material():
                ev = "0"
            else:
                info = engine.analyse(board, chess.engine.Limit(depth=depth))
                ev = fmt_eval(info["score"].white())
            clk = CLK_RE.search(node.comment or "")
            node.comment = (
                "[%%eval %s] [%%clk %s]" % (ev, clk.group(1))
                if clk
                else "[%%eval %s]" % ev
            )
    finally:
        engine.quit()
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
    return game.accept(exporter)


def _worker(args):
    idx, text, depth = args
    try:
        return idx, annotate_game(text, depth)
    except Exception as exc:  # keep the original rather than losing a game
        sys.stderr.write("game %d failed: %s\n" % (idx, exc))
        return idx, text


def split_games(pgn_text):
    return re.split(r"\n\n+(?=\[Event )", pgn_text.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    a = ap.parse_args()

    games = split_games(open(a.infile, encoding="utf-8", errors="replace").read())
    tasks = [(i, g, a.depth) for i, g in enumerate(games)]
    out = [None] * len(games)
    with mp.Pool(a.workers) as pool:
        for n, (i, txt) in enumerate(pool.imap_unordered(_worker, tasks), 1):
            out[i] = txt
            if n % 10 == 0 or n == len(games):
                sys.stderr.write("  %d/%d\n" % (n, len(games)))
                sys.stderr.flush()
    with open(a.outfile, "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(out) + "\n")


if __name__ == "__main__":
    main()
