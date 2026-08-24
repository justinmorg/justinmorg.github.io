#!/usr/bin/env python3
"""
longitudinal.py — compare annotated blocks of jamorgan's corpus over time.

Usage:
    python3 longitudinal.py LABEL=block.pgn [LABEL=block.pgn ...] [--tc 180+2]

Each block is a depth-12 annotated PGN (see annotate.py / annot_inc.py).
Prints, with game-level bootstrap 95% CIs:

  1. Blunder rate (own move drops eval >= 200cp) by move band, and the same
     split by TimeControl so format artifacts are visible.
  2. Hanging-material rate per *eligible winning-middlegame move* — the right
     denominator, not per game. Raw and 0.02 win%-error floored.
  3. Reached >= +200, score from those games, eval after own move 12.

Why the denominator matters: hits-per-game confounds the error rate with how
often you reach a winning position at all. The eligible-move denominator is
exactly hanging.py's selection gate (fullmove > 12, light npm > 14, eval from
your POV >= +150), so a change in the ratio is a change in error rate.

Why --tc matters: 2025 is ~all 3+2 and 2026 is ~half 5+0. Pooling is the
documented default, but anything past move ~25 is clock-sensitive. Pass
--tc 180+2 for a like-for-like comparison; run without it to check whether the
format moved the number.
"""
import os
import random
import statistics as st
import sys
from collections import Counter

import chess
import chess.pgn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import USER, npm, parse_eval, probe  # noqa: E402

random.seed(1729)
BANDS = ("1-12", "13-25", "26+")
FLOOR = 0.02


def band_of(fullmove):
    return "1-12" if fullmove <= 12 else ("13-25" if fullmove <= 25 else "26+")


def boot(vals, B=6000):
    if not vals:
        return float("nan"), float("nan"), float("nan")
    s = sorted(st.mean(random.choices(vals, k=len(vals))) for _ in range(B))
    return st.mean(vals), s[int(0.025 * B)], s[int(0.975 * B)]


def scan(path, tc_filter=None):
    """One pass per block; collects everything the three tables need."""
    d = dict(blunder={b: [] for b in BANDS}, blunder_tc={},
             hits=[], eligible=0, mv12=[], reached=[], converted=[],
             games=0, opp=[])
    with open(path) as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            hw, hb = game.headers.get("White", ""), game.headers.get("Black", "")
            me = chess.WHITE if USER == hw else (chess.BLACK if USER == hb else None)
            if me is None:
                continue
            tc = game.headers.get("TimeControl", "")
            if tc_filter and tc != tc_filter:
                continue
            d["games"] += 1
            try:
                d["opp"].append(int(game.headers["BlackElo" if me == chess.WHITE
                                                else "WhiteElo"]))
            except (KeyError, ValueError):
                pass
            res = game.headers.get("Result")
            score = 0.5 if res == "1/2-1/2" else (
                1.0 if (res == "1-0") == (me == chess.WHITE) else 0.0)

            board, prev, node, ply = game.board(), 0, game, 0
            peak, mv12 = -10 ** 9, None
            stats = {"in_check": 0}
            while node.variations:
                node = node.variations[0]
                move, mover = node.move, board.turn
                ply += 1
                fm = board.fullmove_number
                cp_before = prev if me == chess.WHITE else -prev
                ev = parse_eval(node.comment, mover == chess.WHITE)
                cp_after = None if ev is None else (ev if me == chess.WHITE else -ev)

                if mover == me:
                    if cp_after is not None:
                        blundered = 1.0 if (cp_before - cp_after) >= 200 else 0.0
                        d["blunder"][band_of(fm)].append(blundered)
                        d["blunder_tc"].setdefault((tc, band_of(fm)), []).append(blundered)
                        if fm == 12 and mv12 is None:
                            mv12 = cp_after
                    if fm > 12 and npm(board, "light") > 14:
                        peak = max(peak, cp_before)
                        if cp_before >= 150:
                            d["eligible"] += 1
                            row = probe(board, move, node, me, cp_before,
                                        game, ply, stats)
                            if row:
                                d["hits"].append(row)

                board.push(move)
                prev = ev if ev is not None else prev

            if mv12 is not None:
                d["mv12"].append(mv12)
            d["reached"].append(1.0 if peak >= 200 else 0.0)
            if peak >= 200:
                d["converted"].append(score)
    return d


def pct(t):
    m, lo, hi = t
    return "%5.2f%% [%.2f, %.2f]" % (100 * m, 100 * lo, 100 * hi)


def main():
    argv = sys.argv[1:]
    tc = None
    if "--tc" in argv:
        i = argv.index("--tc")
        tc = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if "=" in a]
    if not args:
        print(__doc__)
        sys.exit(1)

    blocks = {}
    for a in args:
        label, path = a.split("=", 1)
        blocks[label] = scan(path, tc)

    print("time control filter: %s" % (tc or "none (pooled)"))
    for label, d in blocks.items():
        print("  %-10s games=%-5d mean opponent Elo=%s" % (
            label, d["games"],
            "%.0f" % st.mean(d["opp"]) if d["opp"] else "n/a"))

    print("\n=== 1. Blunder rate (own move drops eval >= 200cp), per own move ===")
    for b in BANDS:
        print(" band %s" % b)
        for label, d in blocks.items():
            v = d["blunder"][b]
            print("    %-10s n=%-6d %s" % (label, len(v), pct(boot(v))))

    if not tc:
        print("\n--- same, split by TimeControl (format-artifact check) ---")
        for label, d in blocks.items():
            tcs = sorted({k[0] for k in d["blunder_tc"]})
            for t in tcs:
                v = d["blunder_tc"].get((t, "26+"), [])
                if len(v) >= 200:
                    print("    %-10s %-8s band 26+  n=%-6d %s" % (
                        label, t, len(v), pct(boot(v))))

    print("\n=== 2. Hanging material, per eligible winning-middlegame move ===")
    print("    %-10s %8s %6s  %-22s %6s  %s" % (
        "block", "eligible", "hits", "raw rate", "floored", "floored rate"))
    for label, d in blocks.items():
        n, h = d["eligible"], len(d["hits"])
        fl = sum(1 for r in d["hits"] if r["wp_error"] >= FLOOR)
        raw = boot([1.0] * h + [0.0] * (n - h)) if n else (0, 0, 0)
        flr = boot([1.0] * fl + [0.0] * (n - fl)) if n else (0, 0, 0)
        print("    %-10s %8d %6d  %-22s %6d  %s" % (
            label, n, h, pct(raw), fl, pct(flr)))
    print("    -- floored hits by label --")
    for label, d in blocks.items():
        n = d["eligible"]
        c = Counter(r["label"] for r in d["hits"] if r["wp_error"] >= FLOOR)
        for lab in ("missed their threat", "hung it myself"):
            k = c[lab]
            print("    %-10s %-22s %3d  %s" % (
                label, lab, k, pct(boot([1.0] * k + [0.0] * (n - k)))))

    print("\n=== 3. Winning positions, conversion, opening ===")
    for label, d in blocks.items():
        r = boot(d["reached"])
        c = boot(d["converted"])
        m = boot(d["mv12"])
        print("    %-10s reached>=+200 %s   score-from-won %s   eval@mv12 %+.1fcp [%+.1f, %+.1f]" % (
            label, pct(r), pct(c), m[0], m[1], m[2]))

    print("\nNote: score rate is ~50% in every block by construction "
          "(Lichess matchmaking is self-correcting). Rating level is the\n"
          "improvement metric; score rate and anything measured against "
          "opponents whose strength tracks yours are not.")


if __name__ == "__main__":
    main()
