#!/usr/bin/env python3
"""trades/deep — depth-18 re-check of trades taken after move 12 in the cells the
write-up leans on (both sides). Resumable: skips keys already in OUT.

    python3 deep.py TRADES.csv.gz OUT.jsonl.gz [STOCKFISH]

Cells: Caro Advance (all), Caro Exchange (all), London (random 300 per side,
seed 23). Each row: position before and after the trade, Stockfish depth 18,
Hash 256, mover-POV cp -> Lichess win prob. loss18 = wp18_before - wp18_after.
"""
import sys, os, json, gzip
import pandas as pd, chess, chess.engine
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hanging import winprob

p, out = sys.argv[1], sys.argv[2]
sf = sys.argv[3] if len(sys.argv) > 3 else "/home/claude/sf/x/usr/games/stockfish"
d = pd.read_csv(p, dtype={"gid": str})
T = d[(d.bal == 0) & (d.took == 1) & (d.phase != "opening")]
parts = [T[T.caro == "Advance"].assign(cell="Caro Advance"), T[T.caro == "Exchange"].assign(cell="Caro Exchange")]
for mine in (0, 1):
    x = T[(T.fam == "London") & (T.mine == mine)]
    parts.append(x.sample(min(300, len(x)), random_state=23).assign(cell="London"))
S = pd.concat(parts)
done = set()
if os.path.exists(out):
    for l in gzip.open(out, "rt"):
        r = json.loads(l); done.add((r["gid"], r["fen"]))
eng = chess.engine.SimpleEngine.popen_uci(sf)
eng.configure({"Threads": 2, "Hash": 256})


def cp(board, pov):
    s = eng.analyse(board, chess.engine.Limit(depth=18))["score"].pov(pov)
    return s.score(mate_score=10000)


with gzip.open(out, "at") as fh:
    for i, r in enumerate(S.itertuples()):
        if (r.gid, r.fen) in done:
            continue
        b = chess.Board(r.fen); me = b.turn
        c0 = cp(b, me); b.push_san(r.san); c1 = cp(b, me)
        w0, w1 = winprob(c0), winprob(c1)
        fh.write(json.dumps({"gid": r.gid, "fen": r.fen, "san": r.san, "cell": r.cell, "mine": int(r.mine),
                             "trade_type": r.trade_type, "wp_err": r.wp_err, "cp18_before": c0, "cp18_after": c1,
                             "wp18_before": round(w0, 4), "wp18_after": round(w1, 4), "loss18": round(w0 - w1, 4)}) + "\n")
        fh.flush()
        if i % 100 == 0:
            print(i, len(S), flush=True)
eng.quit()
print("done")
