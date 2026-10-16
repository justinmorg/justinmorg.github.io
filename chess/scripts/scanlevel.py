#!/usr/bin/env python3
"""Sort hanging-material hits by the simplest scan level that catches them.

Each hit's decisive capture (the opponent's best SEE capture after my move,
exactly as hanging.py / build_forward.py pick it) is classified in the
position after my move:

  EXCH  their capture lands on the square I just captured on - an exchange I
        started that nets a loss (the recapture-order case)
  L1    target has no direct defender (pure sight)
  L2    target defended, but the capturing piece is cheaper (value mismatch)
  L3    target defended, capturer not cheaper - only counting finds it

Checked in that order, so each hit gets the first (simplest) level that
applies. A fourth level - a nominal defender that is pinned or overloaded -
is NOT measurable here: SEE counts a pinned defender as a real one, so those
hangs are mostly never flagged in the first place.

Usage:
  scanlevel.py games NAME=file.pgn [NAME=file.pgn ...]
      Baseline blocks. Scope: 180+2 / 300+0, hanging.py's +150 eval gate,
      wp_error > 0.05 (the pre-registered floor).
  scanlevel.py cards [chess-drills/index.html]
      Group F: every H-labelled step on non-decoy cards, plus anchors only.
"""
import sys, os, re, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chess
import hanging as H

TCS = {"180+2", "300+0"}
FLOOR = 0.05
LEVELS = ("L1", "L2", "L3", "EXCH")


def classify(board, move, their_cap_san):
    """board = position before my move, my side to move."""
    me = board.turn
    my_cap_sq = move.to_square if board.is_capture(move) else None
    after = board.copy(stack=False)
    after.push(move)
    cap = after.parse_san(their_cap_san)
    T = cap.to_square
    tgt, capturer = after.piece_at(T), after.piece_at(cap.from_square)
    if my_cap_sq is not None and T == my_cap_sq:
        return "EXCH"
    if not after.attackers(me, T):
        return "L1"
    if H.SEE_VAL[capturer.piece_type] < H.SEE_VAL[tgt.piece_type]:
        return "L2"
    return "L3"


def line(name, counter):
    n = sum(counter.values())
    return f"{name:22s} n={n:4d}  " + "  ".join(
        f"{k}={counter[k]} ({100 * counter[k] / max(1, n):.0f}%)" for k in LEVELS)


def run_games(blocks):
    rows = []
    for name, path in blocks:
        hits, _ = H.scan(path, "light")
        hits = [r for r in hits if r["tc"] in TCS and r["wp_error"] > FLOOR]
        for r in hits:
            b = chess.Board(r["fen"])
            r["block"] = name
            r["lvl"] = classify(b, b.parse_san(r["move_played"]), r["their_capture"])
        rows += hits
        print(line(name, collections.Counter(r["lvl"] for r in hits)))
    print()
    print(line("POOLED", collections.Counter(r["lvl"] for r in rows)))
    for lab in ("missed their threat", "hung it myself"):
        print(line("  " + lab, collections.Counter(r["lvl"] for r in rows if r["label"] == lab)))
    print("\nmean wp_error by level:", {k: round(
        sum(r["wp_error"] for r in rows if r["lvl"] == k) /
        max(1, sum(r["lvl"] == k for r in rows)), 3) for k in LEVELS})


def run_cards(page):
    html = open(page).read()
    m = re.search(r'(\[\{"k":"F-.*?\}\]\}\])', html[html.index("<!--F-START-->"):])
    cards = json.loads(m.group(1))
    allh, anch = collections.Counter(), collections.Counter()
    std, self_ = collections.Counter(), collections.Counter()
    for c in cards:
        if c["decoy"]:
            continue
        anchor = int(c["k"].split("-")[-1])
        b = chess.Board(c["steps"][0]["fen"])
        for st in c["steps"]:
            mv = chess.Move.from_uci(st["m"])
            if st["L"] == "H":
                k = classify(b, mv, st["cap"])
                allh[k] += 1
                (std if st["std"] else self_)[k] += 1
                if st["ply"] == anchor:
                    anch[k] += 1
            b.push(mv)
            if st["r"]:
                b.push_uci(st["r"])
    print(line("F, all H steps", allh))
    print(line("F, anchors only", anch))
    print(line("  standing threat", std))
    print(line("  self-inflicted", self_))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("games", "cards"):
        sys.exit(__doc__)
    if sys.argv[1] == "games":
        run_games([a.split("=", 1) for a in sys.argv[2:]])
    else:
        run_cards(sys.argv[2] if len(sys.argv) > 2 else
                  os.path.join(HERE, "..", "..", "chess-drills", "index.html"))
