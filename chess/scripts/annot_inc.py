#!/usr/bin/env python3
"""Resumable depth-12 annotation. Appends one game at a time and flushes,
so a killed tool call loses at most one game. Re-run until it prints DONE.

Usage: annot_inc.py IN.pgn OUT.pgn [budget_seconds]
"""
import io, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chess, chess.engine, chess.pgn
from annotate import fmt_eval, ENGINE, CLK_RE

inp, outp = sys.argv[1], sys.argv[2]
budget = float(sys.argv[3]) if len(sys.argv) > 3 else 240.0

blocks = [g for g in open(inp, errors='replace').read().split('\n\n\n') if g.strip()]
gid = lambda g: re.search(r'\[GameId "([^"]+)"\]', g).group(1)

done = set()
if os.path.exists(outp):
    done = {gid(g) for g in open(outp, errors='replace').read().split('\n\n\n')
            if g.strip() and 'GameId' in g}

todo = [g for g in blocks if gid(g) not in done]
if not todo:
    print("DONE %d/%d" % (len(done), len(blocks)))
    sys.exit(0)

engine = chess.engine.SimpleEngine.popen_uci(ENGINE)
engine.configure({"Threads": 1, "Hash": 128})
t0 = time.time()
n = 0
try:
    with open(outp, 'a') as out:
        for gtext in todo:
            if time.time() - t0 > budget:
                break
            game = chess.pgn.read_game(io.StringIO(gtext))
            if game is None:
                continue
            board = game.board()
            for node in game.mainline():
                board.push(node.move)
                if board.is_checkmate():
                    ev = "#0"
                elif board.is_stalemate() or board.is_insufficient_material():
                    ev = "0"
                else:
                    ev = fmt_eval(engine.analyse(
                        board, chess.engine.Limit(depth=12))["score"].white())
                clk = CLK_RE.search(node.comment or "")
                node.comment = ("[%%eval %s] [%%clk %s]" % (ev, clk.group(1))
                                if clk else "[%%eval %s]" % ev)
            out.write(str(game) + "\n\n\n")
            out.flush()
            os.fsync(out.fileno())
            n += 1
finally:
    engine.quit()

print("wrote %d this run; %d/%d total" % (n, len(done) + n, len(blocks)))
