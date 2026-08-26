#!/usr/bin/env python3
"""
outcomes.py — where the points actually come from.

Usage:
    python3 outcomes.py LABEL=block.pgn [LABEL=block.pgn ...] [--tc 180+2,300+0]

Two tables `longitudinal.py` doesn't print:

  1. Score from games that never reached >= +200 in the middlegame — the
     complement of longitudinal.py's "score from won positions" row. Same peak
     definition, so `reached` + `not reached` partitions the block exactly.
  2. That bucket split further by the middlegame *trough* — the mirror of peak,
     same eligibility window — so "level all game" is separated from "was lost".
  3. Score by eval on entry to the endgame (first position after move 12 with
     light npm <= 14), over all games regardless of middlegame history.
  4. Wins by termination, and the eval at the moment an opponent flagged, which
     separates "won on the board, clock ran out too" from "rescued by the clock".

Read the never-reached bucket in (1) only alongside (2): about a third of it is
games with no eligible middlegame moves at all, which are not a middlegame state
and score very differently. See the README section for what that does to the
pooled figure.

--tc takes a comma-separated list, unlike longitudinal.py's single value, because
the natural scope here is 3+2 *and* 5+0 together. Flag rates are clock-dependent
by definition, so the per-TC split is always printed regardless of --tc.

Player identity: defaults to CHESS_USER (via hanging.py). For cross-site runs
pass --user-map LABEL=username, matching block labels, e.g.

    --user-map CC-2024=justinmorg CC-2026=justinmorg

Unmapped blocks fall back to the default. Mixing Lichess and chess.com blocks in
one call is the intended use; keep chess.com labelled separately in the output
rather than relying on the pooled row, since it is an independent pool.
"""
import os
import random
import statistics as st
import sys
from collections import Counter

import chess
import chess.pgn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import USER, npm, parse_eval  # noqa: E402

random.seed(1729)

# eval-at-flag buckets, from the player's POV, in centipawns
BUCKETS = (("losing (<-100)", -10 ** 9, -100),
           ("level (-100..+100)", -100, 100),
           ("ahead (+100..+300)", 100, 300),
           ("winning (>+300)", 300, 10 ** 9))


def is_flag(term):
    """True if the game ended on the clock, on either site.

    Lichess writes Termination "Time forfeit". chess.com writes free text —
    "justinmorg won on time", "yossibk5 won on time" — so an equality test
    against "Time forfeit" silently matches zero chess.com games. Same class of
    failure as the CHESS_USER silent zero; see the README.

    chess.com's "won - game abandoned" is a disconnect, not a flag, and is
    deliberately excluded here.
    """
    t = (term or "").lower()
    return t == "time forfeit" or "won on time" in t


def bucket_of(cp):
    for name, lo, hi in BUCKETS:
        if lo < cp <= hi or (lo == -10 ** 9 and cp <= hi):
            return name
    return BUCKETS[-1][0]


def boot(vals, B=6000):
    if not vals:
        return float("nan"), float("nan"), float("nan")
    s = sorted(st.mean(random.choices(vals, k=len(vals))) for _ in range(B))
    return st.mean(vals), s[int(0.025 * B)], s[int(0.975 * B)]


def scan(path, tcs=None, user=None):
    """One pass. Peak definition is longitudinal.py::scan verbatim."""
    user = user or USER
    d = dict(reached=[], notreached=[], games=0, matched=0,
             trough_groups={}, eg_groups={},
             tc=Counter(), wins_tc=Counter(), flagwin_tc=Counter(),
             flagloss_tc=Counter(), flag_bucket=Counter(),
             flag_bucket_nr=Counter(), wins=0, flagwins=0, flagwins_nr=0,
             wins_nr=0)
    with open(path) as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            d["games"] += 1
            hw, hb = game.headers.get("White", ""), game.headers.get("Black", "")
            me = chess.WHITE if user == hw else (chess.BLACK if user == hb else None)
            if me is None:
                continue
            tc = game.headers.get("TimeControl", "")
            if tcs and tc not in tcs:
                continue
            d["matched"] += 1
            d["tc"][tc] += 1

            res = game.headers.get("Result")
            score = 0.5 if res == "1/2-1/2" else (
                1.0 if (res == "1-0") == (me == chess.WHITE) else 0.0)
            term = game.headers.get("Termination", "?")
            flagged = is_flag(term)
            if score == 1.0:
                d["wins"] += 1
                d["wins_tc"][tc] += 1
                if flagged:
                    d["flagwins"] += 1
                    d["flagwin_tc"][tc] += 1
            elif score == 0.0 and flagged:
                d["flagloss_tc"][tc] += 1

            board, prev, node = game.board(), 0, game
            peak, trough, last = -10 ** 9, 10 ** 9, 0
            n_elig, eg_entry = 0, None
            while node.variations:
                node = node.variations[0]
                mover, fm = board.turn, board.fullmove_number
                cp_before = prev if me == chess.WHITE else -prev
                ev = parse_eval(node.comment, mover == chess.WHITE)
                light = npm(board, "light")
                if mover == me and fm > 12 and light > 14:
                    peak = max(peak, cp_before)
                    trough = min(trough, cp_before)
                    n_elig += 1
                if eg_entry is None and fm > 12 and light <= 14:
                    eg_entry = cp_before
                board.push(node.move)
                prev = ev if ev is not None else prev
                last = prev if me == chess.WHITE else -prev

            if eg_entry is not None:
                d["eg_groups"].setdefault(bucket_of(eg_entry), []).append(score)

            if peak >= 200:
                d["reached"].append(score)
            else:
                d["notreached"].append(score)
                if score == 1.0:
                    d["wins_nr"] += 1
                k = ("no eligible middlegame moves" if n_elig == 0 else
                     "even (trough > -200)" if trough > -200 else
                     "losing (-200..-500)" if trough > -500 else "lost (<= -500)")
                d["trough_groups"].setdefault(k, []).append(score)

            if flagged and score == 1.0:
                d["flag_bucket"][bucket_of(last)] += 1
                if peak < 200:
                    d["flag_bucket_nr"][bucket_of(last)] += 1
                    d["flagwins_nr"] += 1
    return d


def main(argv):
    tcs = None
    blocks = []
    umap = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--tc":
            tcs = set(argv[i + 1].split(","))
            i += 2
            continue
        if argv[i] == "--user-map":
            i += 1
            while i < len(argv) and not argv[i].startswith("--") and "=" in argv[i]:
                lab, who = argv[i].split("=", 1)
                umap[lab] = who
                i += 1
            continue
        if "=" not in argv[i]:
            sys.exit(f"expected LABEL=path, got {argv[i]!r}")
        lab, path = argv[i].split("=", 1)
        blocks.append((lab, path))
        i += 1
    if not blocks:
        sys.exit(__doc__)

    print(f"default user: {USER}   time controls: "
          f"{sorted(tcs) if tcs else 'ALL'}"
          + (f"   user map: {umap}" if umap else "") + "\n")
    print(f"{'block':10} {'games':>6} {'reach%':>7} {'score|reached':>14} "
          f"{'score|NOT':>10} {'n(NOT)':>7}")

    allr, alln = [], []
    trough_all, eg_all = {}, {}
    tot = Counter()
    for key in ("tc", "wins_tc", "flagwin_tc", "flagloss_tc",
                "flag_bucket", "flag_bucket_nr"):
        tot[key] = Counter()
    agg = Counter()

    for lab, path in blocks:
        who = umap.get(lab, USER)
        d = scan(path, tcs, who)
        if d["matched"] == 0:
            sys.exit(f"{path}: {d['games']} games read, none matching user "
                     f"{who!r} / tc filter — check --user-map/CHESS_USER and --tc")
        r, n = d["reached"], d["notreached"]
        allr += r
        alln += n
        for key in tot:
            tot[key] += d[key]
        for key in ("wins", "flagwins", "flagwins_nr", "wins_nr"):
            agg[key] += d[key]
        for src_d, dst in ((d["trough_groups"], trough_all),
                           (d["eg_groups"], eg_all)):
            for k, v in src_d.items():
                dst.setdefault(k, []).extend(v)
        print(f"{lab:10} {d['matched']:6d} "
              f"{100 * len(r) / d['matched']:6.1f}% "
              f"{100 * st.mean(r) if r else 0:13.1f}% "
              f"{100 * st.mean(n) if n else 0:9.1f}% {len(n):7d}")

    m, lo, hi = boot(allr)
    m2, lo2, hi2 = boot(alln)
    print(f"\npooled, reached >= +200 : n={len(allr):5d}  "
          f"score {100 * m:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]  "
          f"W{allr.count(1.0)}/D{allr.count(0.5)}/L{allr.count(0.0)}")
    print(f"pooled, never reached   : n={len(alln):5d}  "
          f"score {100 * m2:.1f}% [{100 * lo2:.1f}, {100 * hi2:.1f}]  "
          f"W{alln.count(1.0)}/D{alln.count(0.5)}/L{alln.count(0.0)}")

    print("\nnever-reached, split by middlegame trough:")
    for k in ("even (trough > -200)", "losing (-200..-500)", "lost (<= -500)",
              "no eligible middlegame moves"):
        v = trough_all.get(k, [])
        if not v:
            continue
        m3, lo3, hi3 = boot(v)
        print(f"  {k:30} n={len(v):5d}  score {100 * m3:5.1f}% "
              f"[{100 * lo3:.1f}, {100 * hi3:.1f}]  "
              f"W{v.count(1.0)}/D{v.count(0.5)}/L{v.count(0.0)}")
    real = [s for k, v in trough_all.items() if k != "no eligible middlegame moves"
            for s in v]
    if real:
        m4, lo4, hi4 = boot(real)
        print(f"  {'(excluding no-eligible)':30} n={len(real):5d}  "
              f"score {100 * m4:5.1f}% [{100 * lo4:.1f}, {100 * hi4:.1f}]")

    print("\nscore by eval on entry to the endgame (all games, any history):")
    for name, _, _ in reversed(BUCKETS):
        v = eg_all.get(name, [])
        if not v:
            continue
        m5, lo5, hi5 = boot(v)
        print(f"  {name:22} n={len(v):5d}  score {100 * m5:5.1f}% "
              f"[{100 * lo5:.1f}, {100 * hi5:.1f}]  "
              f"W{v.count(1.0)}/D{v.count(0.5)}/L{v.count(0.0)}")

    if agg["flagwins"] == 0 and agg["wins"]:
        sys.exit("no flag wins found across any block — Termination parsing is "
                 "probably broken for one of these sites; see is_flag()")
    print(f"\nwins by termination: {agg['wins']} wins, {agg['flagwins']} on time "
          f"({100 * agg['flagwins'] / max(1, agg['wins']):.1f}%)")
    for tc in sorted(tot["tc"]):
        n, w = tot["tc"][tc], tot["wins_tc"][tc]
        fw, fl = tot["flagwin_tc"][tc], tot["flagloss_tc"][tc]
        print(f"  {tc:8} games {n:5d}  flag wins {fw:4d} "
              f"({100 * fw / max(1, w):4.1f}% of wins)  "
              f"flag losses {fl:4d} ({100 * fl / n:4.1f}% of games)")

    for label, counter, denom in (
            ("all flag wins", tot["flag_bucket"], agg["flagwins"]),
            ("flag wins in never-reached games", tot["flag_bucket_nr"],
             agg["flagwins_nr"])):
        print(f"\neval when the opponent flagged — {label} (n={denom}):")
        for name, _, _ in BUCKETS:
            c = counter[name]
            print(f"  {name:22} {c:4d}  {100 * c / max(1, denom):5.1f}%")


if __name__ == "__main__":
    main(sys.argv[1:])
