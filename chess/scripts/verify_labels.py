#!/usr/bin/env python3
"""Re-evaluate every group F step where SEE finds material, at depth 18.

Why. The H/C/S label in build_forward.py ANDs two things: a SEE probe that
finds a capture worth >=150, and a drop in the stored depth-12 eval. SEE only
looks at one square, so it cannot see a *bigger counter-threat elsewhere* -
the c7 pawn attacking the queen while the bishop takes on f3. The C label
exists for exactly that case and depends entirely on the eval to catch it, so
any depth-12 wobble larger than the floor flips a compensated move into a
"you hung a piece" verdict.

Found 2026-09-03 by Justin, on card 8 (`F-DrQ8aRNG-43`, 21.bxc7): the corpus
carries +1.12 -> +0.77 and labelled it H; fresh Stockfish gives +4.65 -> +4.75
at depths 12 and 18 and calls bxc7 the top move. The drill marked a winning
move as a blunder.

Measured rate over all 345 H-labelled and 62 C-labelled steps:

  * 36 of 345 H steps (10.4%) are not losses at depth 18; in 15 the played
    move was the engine's first choice.
  * Strongly concentrated at small eval drops. Where the stored drop was
    <= 0.05 win-probability, 41% are false positives. Where it was > 0.10,
    1 of 212 is (0.5%).
  * 1 of 62 C steps goes the other way and does lose material.
  * On the 239 group P hit plies specifically, 21 (8.8%) are not errors, 8 of
    them the engine's top move.

Two fixes follow, both applied: FLOOR moves 0.02 -> 0.05 in build_forward.py
and build_drills2.py, and the drill labels are set from this cache rather than
from the depth-12 evals. The floor alone takes H false positives to 2.5%; the
cache takes the drill to 0.

This writes chess/data/depth18_verify.json, which IS committed - the drill
build must be reproducible without an engine. Re-run only when the card set
changes; it is resumable and takes ~7 minutes for ~400 positions.

    python3 chess/scripts/verify_labels.py [index.html] [out.json]

Depth 18 not 12 because the README's own caveat says depth 12 is noisy above
+5 and these are winning positions; not deeper because 18 already agrees with
20 on every spot-check and the cost doubles.
"""
import json, os, re, sys, time
import chess, chess.engine

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PAGE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "chess-drills/index.html")
OUT  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "chess/data/depth18_verify.json")
SF   = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
DEPTH = 18
TMP = OUT + ".partial.jsonl"

src = open(PAGE).read()
m = re.search(r'<script type="application/json" id="fdata">(.*?)</script>', src, re.S)
if not m:
    sys.exit("ERROR: no group F data in the page - run build_forward.py first")
cards = json.loads(m.group(1))

# Every step whose SEE probe found material, either side of the played move.
jobs = {}
for c in cards:
    b = chess.Board(c["steps"][0]["fen"])
    for st in c["steps"]:
        if st["L"] in ("H", "C"):
            jobs.setdefault(b.fen() + "|" + st["m"], (b.fen(), st["m"]))
        b.push_uci(st["m"])
        if st["r"]:
            b.push_uci(st["r"])

# Accumulate: never drop an entry. Labels feed back into which cards exist, so
# a cache trimmed to the current card set makes the build oscillate - a card
# cleared on one pass loses its entry, falls back to depth-12 on the next, and
# comes back. The union is small and always safe.
done = {}
if os.path.exists(OUT):
    try:
        done = {k: v for k, v in json.load(open(OUT))["evals"].items()}
    except Exception:
        done = {}
if os.path.exists(TMP):
    for line in open(TMP):
        r = json.loads(line)
        done[r["key"]] = r
todo = [k for k in jobs if k not in done]
print(f"{len(jobs)} positions, {len(done)} cached, {len(todo)} to do")

if todo:
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    t0 = time.time()
    with open(TMP, "a") as fh:
        for k in todo:
            fen, uci = jobs[k]
            b = chess.Board(fen)
            me = b.turn
            i1 = eng.analyse(b, chess.engine.Limit(depth=DEPTH))
            rec = {"key": k,
                   "fb": i1["score"].pov(me).score(mate_score=10000),
                   "best": b.san(i1["pv"][0])}
            b.push_uci(uci)
            rec["fa"] = eng.analyse(b, chess.engine.Limit(depth=DEPTH))["score"].pov(me).score(mate_score=10000)
            done[k] = rec
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
    eng.quit()
    print(f"  {len(todo)} in {time.time()-t0:.0f}s")

evals = {k: {"fb": v["fb"], "fa": v["fa"], "best": v["best"]} for k, v in done.items()}
json.dump({
    "depth": DEPTH,
    "engine": "Stockfish 16 (debian stockfish package)",
    "generated": time.strftime("%Y-%m-%d"),
    "note": ("Fresh depth-18 evals for every group F step where SEE>=150, both sides of the "
             "played move, own POV in centipawns. Keyed 'FEN|uci'. Built by "
             "chess/scripts/verify_labels.py; consumed by build_forward.py, which prefers "
             "these over the depth-12 corpus evals when setting the H/C/S label."),
    "evals": evals,
}, open(OUT, "w"), indent=0, sort_keys=True)
print(f"wrote {OUT}: {len(evals)} entries")
