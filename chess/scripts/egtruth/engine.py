#!/usr/bin/env python3
"""egtruth/engine — deeper second opinion on > 7-man endgame plies.

Stockfish 17.1, 2 threads, 256 MB hash, MultiPV 4, fixed 150k nodes per
position (about depth 16-20 in these endings, vs depth 12 in the corpus).
If the move actually played is not among the top 4, a second search
restricted to that move (same node budget) gives its score.

    python3 engine.py rows.csv.gz OUT.jsonl BAND [STOCKFISH_PATH]

BAND: "close" = depth-12 mover win chance 0.25-0.75 before the move;
      "ahead" = 0.75-0.95.  Both sides' moves.  Resumable.

Line: {"gid","ply","pv":[[uci, cp_mover]...best first], "played":[uci, cp_mover], "depth": d}
cp is mover POV; mate = +/-10000 (sign = mover mates / is mated).
"""
import sys, os, csv, gzip, json, time
import chess, chess.engine

SF = "/home/claude/sf/sf17/stockfish/stockfish-ubuntu-x86-64-avx2"
NODES = 150000


def cp(score, pov):
    s = score.pov(pov)
    if s.is_mate():
        return 10000 if s.mate() > 0 else -10000
    return s.score()


def main(rows, out, band, sf=SF):
    lo, hi = {"close": (0.25, 0.75), "ahead": (0.75, 0.95)}[band]
    done = set()
    if os.path.exists(out):
        for line in open(out):
            try:
                d = json.loads(line)
                done.add((d["gid"], d["ply"]))
            except Exception:
                pass
    todo = []
    with gzip.open(rows, "rt") as fh:
        for r in csv.DictReader(fh):
            if int(r["men"]) <= 7 or r["wp_before"] == "":
                continue
            if lo <= float(r["wp_before"]) <= hi and (r["gid"], int(r["ply"])) not in done:
                todo.append((r["gid"], int(r["ply"]), r["fen"], r["uci"]))
    print(len(todo), "to do", flush=True)
    eng = chess.engine.SimpleEngine.popen_uci(sf)
    eng.configure({"Threads": 2, "Hash": 256})
    fo = open(out, "a")
    t0 = time.time()
    for i, (gid, ply, fen, uci) in enumerate(todo):
        b = chess.Board(fen)
        pov = b.turn
        info = eng.analyse(b, chess.engine.Limit(nodes=NODES), multipv=4)
        pv = [[x["pv"][0].uci(), cp(x["score"], pov)] for x in info if "pv" in x and x["pv"]]
        depth = info[0].get("depth")
        got = dict(pv)
        if uci in got:
            played = [uci, got[uci]]
        else:
            x = eng.analyse(b, chess.engine.Limit(nodes=NODES), root_moves=[chess.Move.from_uci(uci)])
            played = [uci, cp(x["score"], pov)]
        fo.write(json.dumps({"gid": gid, "ply": ply, "pv": pv, "played": played, "depth": depth},
                            separators=(",", ":")) + "\n")
        if (i + 1) % 500 == 0:
            fo.flush()
            el = time.time() - t0
            print(i + 1, "%.0fs, eta %.0f min" % (el, el / (i + 1) * (len(todo) - i - 1) / 60), flush=True)
    fo.close()
    eng.quit()
    print("done", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
