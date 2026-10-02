#!/usr/bin/env python3
"""
depthlabel.py — at what search depth does a blunder become visible?

Pre-specification: `depthlabel_prespec.md` (committed before any output).

Two subcommands:

    python3 depthlabel.py keys moves.csv.gz fens.csv.gz keys.csv \\
        LABEL=file.pgn [LABEL=file.pgn ...] [--user-map LABEL=user ...]

        Selects the population (prespec §Population), recovers the move that
        was actually played by walking the source PGNs, and checks that the
        board at (gid, ply) reproduces the FEN `features.py --emit-fens all`
        wrote. Any mismatch is a hard exit: the FEN file is the authority and
        this walk only borrows the move.

    python3 depthlabel.py run keys.csv out.jsonl [budget_s]

        Resumable engine pass on the `annot_inc.py` / `multipv.py` pattern:
        appends and fsyncs one JSON line per position, resumes by (gid, ply),
        re-run until it prints `DONE n/n`. Positions are processed in a seeded
        shuffled order (prespec §Order) so a partial file is a random subsample,
        never a single block — see "the resumability trap" in the README.

Per position and per depth d in DEPTHS, two independent searches from an empty
hash (`ucinewgame` before every search, so a deeper search can never leak into
a shallower one through the transposition table):

    best_d   = score of the unrestricted search at depth d (mover POV)
    played_d = score of the search restricted to the played move at depth d

    loss_d   = best_d - played_d, mate scores mapped to +/-10000 as elsewhere

If the unrestricted search's first move *is* the played move, loss_d = 0 and
the restricted search is skipped (it would return the same line).

Output, one JSON object per line:

    gid, ply, uci, best_cp{d}, played_cp{d}, loss{d}, best_move{d}

for d in DEPTHS. Labels (detect depth, confirmed, monotone) are derived in the
analysis script, not here, so the thresholds stay arguable without a re-run.

Cost: dominated by depth 12, roughly 0.1-0.4 s per position single-core.
"""
import csv
import gzip
import json
import os
import random
import sys
import time

import chess
import chess.engine
import chess.pgn

ENGINE = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
DEPTHS = (1, 2, 4, 8, 12)
MATE = 10000
SEED = 20261002


def opener(p):
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


# ---------------------------------------------------------------- keys

def population(moves_path):
    """Prespec §Population. Same scope as the README think-time section."""
    out = {}
    with opener(moves_path) as fh:
        for r in csv.DictReader(fh):
            try:
                spend = float(r["spend"])
            except ValueError:
                continue
            if not (int(r["fullmove"]) > 12 and r["mate_flag"] == "0"
                    and 0 <= spend <= 60 and int(r["drop_cp"]) >= 200):
                continue
            out[(r["gid"], int(r["ply"]))] = r
    return out


def cmd_keys(argv):
    moves_path, fens_path, keys_out = argv[:3]
    rest = argv[3:]
    blocks, umap = [], {}
    i = 0
    while i < len(rest):
        if rest[i] == "--user-map":
            i += 1
            while i < len(rest) and not rest[i].startswith("--"):
                k, v = rest[i].split("=", 1)
                umap[k] = v
                i += 1
            continue
        k, v = rest[i].split("=", 1)
        blocks.append((k, v))
        i += 1

    pop = population(moves_path)
    fens = {}
    with opener(fens_path) as fh:
        for r in csv.DictReader(fh):
            key = (r["gid"], int(r["ply"]))
            if key in pop:
                fens[key] = r["fen"]
    missing = set(pop) - set(fens)
    if missing:
        sys.exit(f"{len(missing)} population rows have no FEN; "
                 "run features.py with --emit-fens all")

    found = {}
    for label, path in blocks:
        user = umap.get(label, "jamorgan")
        with open(path) as fh:
            while True:
                g = chess.pgn.read_game(fh)
                if g is None:
                    break
                if user not in (g.headers.get("White"), g.headers.get("Black")):
                    continue
                gid = g.headers.get("GameId", "")
                b, ply = g.board(), 0
                for mv in g.mainline_moves():
                    ply += 1
                    key = (gid, ply)
                    if key in pop and key not in found:
                        if b.fen() != fens[key]:
                            sys.exit(f"FEN mismatch at {key}: walk {b.fen()} "
                                     f"vs features {fens[key]}")
                        found[key] = (b.fen(), mv.uci())
                    b.push(mv)
    lost = set(pop) - set(found)
    if lost:
        sys.exit(f"{len(lost)} population rows not found in the PGNs given")

    with open(keys_out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gid", "ply", "fen", "uci"])
        for key in sorted(found):
            w.writerow([key[0], key[1], *found[key]])
    print(f"{len(found)} keys -> {keys_out} (every FEN matched)")


# ---------------------------------------------------------------- run

def cp(score, turn):
    return score.pov(turn).score(mate_score=MATE)


def label_one(eng, fen, uci):
    b = chess.Board(fen)
    mv = chess.Move.from_uci(uci)
    rec = {}
    for d in DEPTHS:
        info = eng.analyse(b, chess.engine.Limit(depth=d), game=object())
        best = cp(info["score"], b.turn)
        bm = info["pv"][0] if info.get("pv") else None
        if bm == mv:
            played = best
        else:
            info2 = eng.analyse(b, chess.engine.Limit(depth=d),
                                root_moves=[mv], game=object())
            played = cp(info2["score"], b.turn)
        rec[f"best_cp{d}"] = best
        rec[f"played_cp{d}"] = played
        rec[f"loss{d}"] = best - played
        rec[f"best_move{d}"] = bm.uci() if bm else None
    return rec


def cmd_run(argv):
    keys_path, out_path = argv[:2]
    budget = float(argv[2]) if len(argv) > 2 else 1e9
    with open(keys_path) as fh:
        keys = list(csv.DictReader(fh))
    random.Random(SEED).shuffle(keys)
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue            # torn last line from a killed run
                done.add((j["gid"], j["ply"]))
    todo = [k for k in keys if (k["gid"], int(k["ply"])) not in done]
    eng = chess.engine.SimpleEngine.popen_uci(ENGINE)
    eng.configure({"Threads": 1, "Hash": 16})
    t0, n = time.time(), 0
    try:
        with open(out_path, "a") as out:
            for k in todo:
                if time.time() - t0 > budget:
                    break
                rec = {"gid": k["gid"], "ply": int(k["ply"]), "uci": k["uci"]}
                rec.update(label_one(eng, k["fen"], k["uci"]))
                out.write(json.dumps(rec) + "\n")
                out.flush()
                os.fsync(out.fileno())
                n += 1
    finally:
        eng.quit()
    total = len(done) + n
    tag = "DONE" if total >= len(keys) else "PARTIAL"
    print(f"{tag} {total}/{len(keys)}  (+{n} in {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    {"keys": cmd_keys, "run": cmd_run}[sys.argv[1]](sys.argv[2:])
