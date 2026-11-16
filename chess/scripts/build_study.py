#!/usr/bin/env python3
"""build_study — manifest for /chess-study, and the one entry point.

    python3 build_study.py            rebuild chess-study/data/index.json from the deck files
    python3 build_study.py --all      rebuild every deck first (routine, endgames, openings)

The page (chess-study/index.html) is static and hand-maintained; only the
JSON under chess-study/data/ is generated. Nothing here touches
chess-drills/ in any way: the frozen group F page and its localStorage keys
(drills.done.v1, drills.forward.v1) are left alone, and this page stores under
its own key, study.v1.

Offline rebuild: the tablebase and engine caches in chess/study/ are
committed, so --all reproduces the decks byte-identically without network or
Stockfish as long as the corpus files are unchanged.
"""
import os, sys, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "chess-study", "data")
BUILT = "2026-11-16"

GROUPS = [
    {"title": "The move routine",
     "blurb": "The pre-move check: two looks for blitz, four steps when there is time. Read the first three, then work down the ladder. Every key is computed from the rules alone, with no engine.",
     "decks": [
         ("routine", "R", "lesson", "The routine", "The two looks, the four steps, and what a threat is. Five minutes."),
         ("anatomy", "A", "lesson", "Anatomy of a hang", "Pieces you lost in your own games, taken apart by cause."),
         ("walk", "W", "lesson", "Worked walkthroughs", "The whole routine run move by move on three stretches of your games."),
         ("s1", "S1", "drill", "Checks", "Warm-up. Every piece that can give check, both sides."),
         ("s2", "S2", "drill", "Takes", "Warm-up. What can be captured, and which captures win material."),
         ("s3", "S3", "drill", "Loose pieces", "Warm-up. Undefended, or attacked by something cheaper."),
         ("s4", "S4", "drill", "Lands, leaves", "Look 2. The move is named, not shown: is it safe where it lands, and what did it stop guarding?"),
         ("s5", "S5", "drill", "Two moves in a row", "They move twice. Find the biggest threat, or say there is none."),
         ("s5b", "S5b", "drill", "A different piece", "The threats you said you cannot picture: one piece moves, another captures."),
         ("s6", "S6", "drill", "The two looks", "Both looks on four to six consecutive moves of a real game. Replaces the play-forward cards."),
     ]},
    {"title": "Endgames",
     "blurb": "Your widest gap against same-rated opponents is in close endgames, most of all with a passed pawn on the board. Lessons first, then drills, then play-outs of your own positions against the computer.",
     "decks": [
         ("eg_lessons", "E", "lesson", "Endgame lessons", "Nine short lessons in the order your games suggest. Checked move by move against a tablebase."),
         ("eg_own", "PP", "drill", "Your passed pawns", "Close endgames from your games where a passed pawn was mishandled. Find the better move. Engine-judged."),
         ("eg_kpk", "KP", "drill", "King and pawn: the only move", "One move wins or one move draws. Opposition and key squares."),
         ("eg_square", "SQ", "drill", "The square of the pawn", "Does it queen, or does the king catch it? Answer without counting."),
         ("eg_rook", "RK", "drill", "Rook-ending methods", "Build the bridge, hold the third rank, put the rook behind the pawn."),
         ("k1", "K1", "playout", "Play-outs: small edge", "Your endgames at one to three pawns up that you did not win. Play them out on Lichess."),
         ("k2", "K2", "playout", "Play-outs: should be over", "Three to six pawns up and not won. Play them out until they are."),
     ]},
    {"title": "Openings",
     "blurb": "Openings are your strength, so this is a patch and not a course: the handful of lines where your games repeat the same error, the one London position you keep re-solving, and a default against first moves you have no reply to.",
     "decks": [
         ("op_lessons", "O", "lesson", "Opening lessons", "Move-by-move, with the idea behind each move and which moves do not matter."),
         ("op_drills", "OD", "drill", "Your move", "The positions from the lessons, and the exact spots where your games went wrong more than once."),
     ]},
]


def main():
    if "--all" in sys.argv:
        for script in ("build_study_routine.py", "build_study_endgames.py", "build_study_openings.py"):
            subprocess.check_call([sys.executable, os.path.join(HERE, script)])
    groups = []
    for g in GROUPS:
        decks = []
        for did, tag, kind, title, blurb in g["decks"]:
            p = os.path.join(OUT, did + ".json")
            if not os.path.exists(p):
                print("missing deck, skipped:", did)
                continue
            d = json.load(open(p, encoding="utf-8"))
            decks.append({"id": did, "tag": tag, "kind": kind, "title": title, "blurb": blurb,
                          "keys": [c["k"] for c in d["cards"]]})
        groups.append({"title": g["title"], "blurb": g["blurb"], "decks": decks})
    man = {"built": BUILT,
           "lede": "Lessons, drills and play-outs built from your own games.",
           "note": "Built on 2026-11-16 while the 900-game block was still running. Nothing here is meant to be opened for practice until that block is closed and scored.",
           "groups": groups}
    json.dump(man, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False,
              separators=(",", ":"), sort_keys=True)
    n = sum(len(d["keys"]) for g in groups for d in g["decks"])
    print("manifest: %d decks, %d cards" % (sum(len(g["decks"]) for g in groups), n))


if __name__ == "__main__":
    main()
