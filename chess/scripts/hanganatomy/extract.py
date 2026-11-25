#!/usr/bin/env python3
"""Step 1 of the hang-anatomy study: collect every floored hanging-material hit.

Same selection as blockstats.py's `hang` metric at the pre-registered 0.05
floor (probe() from hanging.py, fullmove > 12, light npm > 14, cp_before >=
+150, wp_error >= 0.05, --tc 180+2,300+0), so the per-block counts must
reproduce the published table (rate x eligible). For each hit it also stores
what the engine step and the trajectory step need: the game's mainline as UCI,
the stored depth-12 evals and clocks per ply, and the opponent's previous move.

    python3 extract.py OUT.json LABEL=path.pgn [LABEL=path.pgn ...]
"""
import json, os, re, sys
import chess, chess.pgn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from hanging import npm, parse_eval, probe, winprob  # noqa: E402

USER = os.environ.get("CHESS_USER", "jamorgan")
TC = {"180+2", "300+0"}
FLOOR = 0.05
CLK_RE = re.compile(r"\[%clk (\d+):(\d+):(\d+)\]")


def clk(comment):
    m = CLK_RE.search(comment or "")
    return None if not m else int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])


def run(label, path, out):
    n_games = n_elig = 0
    with open(path, errors="replace") as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            if game.headers.get("TimeControl") not in TC:
                continue
            hw, hb = game.headers.get("White", ""), game.headers.get("Black", "")
            if USER == hw:
                me = chess.WHITE
            elif USER == hb:
                me = chess.BLACK
            else:
                continue
            n_games += 1
            mainline, clocks = [], []
            for node in game.mainline():
                mainline.append(node.move.uci())
                clocks.append(clk(node.comment))
            # evals: white-POV cp per ply, carried forward like hanging.py does
            board, prev, ply, node = game.board(), 0, 0, game
            ev_w, hits = [], []
            stats = {"in_check": 0}
            while node.variations:
                node = node.variations[0]
                move, mover = node.move, board.turn
                ply += 1
                cp_before = prev if me == chess.WHITE else -prev
                ev = parse_eval(node.comment, mover == chess.WHITE)
                if (mover == me and board.fullmove_number > 12
                        and npm(board, "light") > 14 and cp_before >= 150):
                    n_elig += 1
                    r = probe(board, move, node, me, cp_before, game, ply, stats)
                    if r and r["wp_error"] >= FLOOR:
                        hits.append(r)
                board.push(move)
                prev = ev if ev is not None else prev
                ev_w.append(prev)
            for r in hits:
                r["block"] = label
                r["moves"] = mainline
                r["evals_w"] = ev_w
                r["clocks"] = clocks
                r["white"], r["black"] = hw, hb
                r["termination"] = game.headers.get("Termination", "")
                out.append(r)
    return n_games, n_elig


if __name__ == "__main__":
    dst = sys.argv[1]
    out, summary = [], []
    for arg in sys.argv[2:]:
        label, path = arg.split("=", 1)
        before = len(out)
        g, e = run(label, path, out)
        k = len(out) - before
        summary.append((label, g, e, k))
        print(f"{label:8s} games {g:5d}  eligible {e:6d}  hits {k:4d}  "
              f"rate {100*k/max(e,1):.2f}%", flush=True)
    json.dump(out, open(dst, "w"))
    print(f"wrote {dst}: {len(out)} hits")
