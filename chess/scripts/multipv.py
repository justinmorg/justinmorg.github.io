#!/usr/bin/env python3
"""
multipv.py — how many moves actually hold the advantage, per position.

Usage:
    python3 multipv.py fens.csv.gz out.jsonl [budget_s] \
        [--depth 16] [--multipv 8] [--keys keys.csv]

Answers the difficulty question `features.py` cannot: a position where only one
move holds is not the same task as one where four do, and without that the
think-time gradient in the README is uninterpretable — long thinks select hard
positions by construction.

Resumable, on the `annot_inc.py` pattern and for the same reason: sandbox
commands have a time limit and background jobs do not survive between them, so
a single long run loses everything. Appends and fsyncs after each position and
resumes by `(gid, ply)`. Re-run until it prints `DONE n/n`.

    --keys  restricts to a subset, as a CSV with gid,ply columns. The natural
            subset is the fast/slow contrast rows rather than every position;
            the middle of the spend range carries no weight in that comparison.

Output, one JSON object per line:

    gid, ply, depth, multipv, best_cp, n_within_50, n_within_100, n_within_200,
    best_move, saturated

`saturated` is true when every line searched came within the threshold, i.e.
the true count may exceed `--multipv`. Bin coarsely — only-move (1) / narrow
(2-3) / wide (4+) — rather than using the raw count: on a depth-16 vs depth-20
spot check the raw counts disagreed in 5 of 12 positions while the coarse bins
were far more stable.

Cost, measured single-core, multipv 8: depth 16 is ~1.3-1.5 s/position, depth
20 is ~7.4. Depth 20 is not worth 5x here.
"""
import csv
import gzip
import json
import os
import sys
import time

import chess
import chess.engine

ENGINE = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
MATE = 10000


def load_keys(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as fh:
        return {(r["gid"], int(r["ply"])) for r in csv.DictReader(fh)}


def main(argv):
    depth, multipv, keys_path = 16, 8, None
    pos_args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--depth":
            depth = int(argv[i + 1]); i += 2; continue
        if argv[i] == "--multipv":
            multipv = int(argv[i + 1]); i += 2; continue
        if argv[i] == "--keys":
            keys_path = argv[i + 1]; i += 2; continue
        pos_args.append(argv[i]); i += 1
    if len(pos_args) < 2:
        sys.exit(__doc__)
    fens_path, out_path = pos_args[0], pos_args[1]
    budget = float(pos_args[2]) if len(pos_args) > 2 else 240.0

    op = gzip.open if fens_path.endswith(".gz") else open
    with op(fens_path, "rt") as fh:
        todo = [(r["gid"], int(r["ply"]), r["fen"]) for r in csv.DictReader(fh)]
    if keys_path:
        keep = load_keys(keys_path)
        todo = [t for t in todo if (t[0], t[1]) in keep]

    done = set()
    if os.path.exists(out_path):
        with open(out_path) as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    done.add((d["gid"], d["ply"]))
                except (ValueError, KeyError):
                    continue
    todo = [t for t in todo if (t[0], t[1]) not in done]
    total = len(done) + len(todo)
    if not todo:
        print(f"DONE {len(done)}/{total}")
        return

    if not os.path.exists(ENGINE):
        sys.exit(f"no engine at {ENGINE} — see the README's Stockfish section, "
                 f"or set STOCKFISH_PATH")
    eng = chess.engine.SimpleEngine.popen_uci(ENGINE)
    eng.configure({"Threads": 1, "Hash": 128})
    t0, n = time.time(), 0
    with open(out_path, "a") as out:
        for gid, ply, fen in todo:
            if time.time() - t0 > budget:
                break
            b = chess.Board(fen)
            info = eng.analyse(b, chess.engine.Limit(depth=depth), multipv=multipv)
            scores = [i["score"].pov(b.turn).score(mate_score=MATE) for i in info]
            best = scores[0]
            rec = {"gid": gid, "ply": ply, "depth": depth, "multipv": multipv,
                   "best_cp": best,
                   "n_within_50": sum(1 for s in scores if best - s <= 50),
                   "n_within_100": sum(1 for s in scores if best - s <= 100),
                   "n_within_200": sum(1 for s in scores if best - s <= 200),
                   "best_move": b.san(info[0]["pv"][0]),
                   "saturated": len(scores) == multipv
                                and best - scores[-1] <= 100}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            os.fsync(out.fileno())
            n += 1
    eng.quit()
    fin = len(done) + n
    if fin >= total:
        print(f"DONE {fin}/{total}")
    else:
        rate = (time.time() - t0) / max(n, 1)
        print(f"{fin}/{total}  (+{n} this call, {rate:.2f} s/pos, "
              f"~{(total - fin) * rate / 60:.0f} min left)")


if __name__ == "__main__":
    main(sys.argv[1:])
