#!/usr/bin/env python3
"""egtruth/verify — depth-20 check of a random sample of the engine-pass labels.

    python3 verify.py eng_rows.csv.gz OUT.jsonl [n_err=200] [n_ok=100]

From the close > 7-man rows written by analyze.py: n_err random "errors"
(gap >= 0.15 at 150k nodes) and n_ok random non-errors, per side (him / opp),
seed 11. Each gets SF17.1 depth 20 (3 s cap) on the best move and on the move
played. Line: {gid, ply, mine, src: err|ok, gap20}.
"""
import sys, json, math
import pandas as pd, chess, chess.engine

SF = "/home/claude/sf/sf17/stockfish/stockfish-ubuntu-x86-64-avx2"


def wp(cp):
    cp = max(-1000, min(1000, cp))
    return 1 / (1 + math.exp(-0.00368208 * cp))


def sc(s, pov):
    s = s.pov(pov)
    return (10000 if s.mate() > 0 else -10000) if s.is_mate() else s.score()


def main(rows, out, n_err=200, n_ok=100):
    c = pd.read_csv(rows)
    parts = []
    for mine in (1, 0):
        s = c[c.mine == mine]
        parts.append(s[s.deeperr == 1].sample(int(n_err), random_state=11).assign(src="err"))
        parts.append(s[s.deeperr == 0].sample(int(n_ok), random_state=11).assign(src="ok"))
    smp = pd.concat(parts)
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    eng.configure({"Threads": 2, "Hash": 256})
    lim = chess.engine.Limit(depth=20, time=3)
    with open(out, "w") as fo:
        for i, r in enumerate(smp.itertuples()):
            b = chess.Board(r.fen)
            pov = b.turn
            best = eng.analyse(b, lim)
            bm = best["pv"][0]
            bcp = sc(best["score"], pov)
            if bm.uci() == r.uci:
                pcp = bcp
            else:
                pl = eng.analyse(b, lim, root_moves=[chess.Move.from_uci(r.uci)])
                pcp = sc(pl["score"], pov)
            bw = 1.0 if bcp >= 10000 else 0.0 if bcp <= -10000 else wp(bcp)
            pw = 1.0 if pcp >= 10000 else 0.0 if pcp <= -10000 else wp(pcp)
            fo.write(json.dumps({"gid": r.gid, "ply": int(r.ply), "mine": int(r.mine), "src": r.src,
                                 "gap20": round(bw - pw, 4)}) + "\n")
            if (i + 1) % 50 == 0:
                fo.flush()
                print(i + 1, flush=True)
    eng.quit()


if __name__ == "__main__":
    main(*sys.argv[1:])
