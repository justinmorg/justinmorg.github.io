#!/usr/bin/env python3
"""
ratingexcursion.py — did a rating excursion reflect better play, or a random walk?

Usage:
    python3 ratingexcursion.py corpus.pgn \
        --window 2026-01-20:2026-02-14 [--window 2026-02-04:2026-02-14] \
        [--tc 180+2] [--until 2026-04-30] [--seed 23] [--shuffles 20000]

Built Aug 2026 for the Jan/Feb 2026 peak (1508 on 2026-02-06, the all-time
Lichess blitz high). Reusable for any future excursion — trigger 2 in "When it
is worth pulling a fresh batch" exists precisely to flag these, and this is the
script that adjudicates one without annotating a new block.

WHY THE OBVIOUS TEST IS WRONG
-----------------------------
The window is selected *because* the results were good. Nearly every move-quality
measure correlates with winning, so under a null of constant skill the
best-results window still shows better-looking quality. A plain window-vs-rest
permutation is therefore biased toward finding improvement. It is reported as T3
for contrast only and must not be quoted as evidence.

The headline test (T2) reproduces the selection inside the null: each shuffle
re-runs the same cherry-pick — find the hottest k-game window in the shuffled
order — and measures *that* window's quality. The observed window is then
compared against windows selected the same way by luck alone.

TESTS
-----
T1  Was the streak itself extreme?  Permute game order; record the best k-game
    score anywhere in the shuffled series; p = P(shuffled best >= observed best).
T2  Selection-aware quality test (headline). As above, but record the selected
    window's quality metrics. One-sided toward *better* play.
T3  Naive window-vs-rest permutation. Biased; contrast only.

METRICS
-------
Blunder rate and the hanging-material gate mirror longitudinal.py / hanging.py
exactly, so rates printed here agree with those scripts. `wploss` is mean win
probability lost per own move (Lichess logistic, clipped at 0) — the
highest-power accuracy measure available without re-running an engine.

VALIDATION GATE
---------------
Refuses to print results unless it reproduces the published 2026 figures:
1,515 games; 3+2 blunder bands 3.27 / 9.85 / 9.68; 3+2 eligible 2,640 at 4.73%
floored; all-TC eligible 5,529 at 4.32% (note: that is *every* time control —
the README's 5,517 / 4.33% is the 3+2-and-5+0 corpus default, which drops 4
games at 300+3 and 180+0); hanging.py's 368 raw hits. Skipped automatically if
the input is not the 2026 corpus.
"""
import argparse
import datetime
import os
import random
import statistics as st
import sys

import chess
import chess.pgn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hanging import USER, npm, parse_eval, probe, winprob  # noqa: E402

FLOOR = 0.02
GATE_2026 = dict(games=1515, b112=3.27, b1325=9.85, b26=9.68,
                 el32=2640, hang32=4.73, elall=5529, hangall=4.32, hits=368)


def band_of(fm):
    return "1-12" if fm <= 12 else ("13-25" if fm <= 25 else "26+")


def scan(path):
    """One row per game: rating path plus the quality counters."""
    rows = []
    with open(path) as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            h = game.headers
            me = (chess.WHITE if USER == h.get("White", "")
                  else (chess.BLACK if USER == h.get("Black", "") else None))
            if me is None:
                continue
            res = h.get("Result")
            score = 0.5 if res == "1/2-1/2" else (
                1.0 if (res == "1-0") == (me == chess.WHITE) else 0.0)

            def ihdr(k):
                try:
                    return int(h.get(k, "").replace("+", ""))
                except ValueError:
                    return None

            side = "White" if me == chess.WHITE else "Black"
            other = "Black" if me == chess.WHITE else "White"
            r = dict(gid=h.get("GameId", ""),
                     date=h.get("UTCDate", "").replace(".", "-"),
                     time=h.get("UTCTime", "00:00:00"),
                     tc=h.get("TimeControl", ""), score=score,
                     my_elo=ihdr(side + "Elo"), opp_elo=ihdr(other + "Elo"),
                     rdiff=ihdr(side + "RatingDiff") or 0,
                     eligible=0, floored=0, hits=0,
                     wploss_sum=0.0, wploss_n=0, peak=-10 ** 9)
            for b in ("1-12", "13-25", "26+"):
                r["bl_" + b], r["bn_" + b] = 0, 0

            board, prev, node, ply = game.board(), 0, game, 0
            stats = {"in_check": 0}
            while node.variations:
                node = node.variations[0]
                move, mover = node.move, board.turn
                ply += 1
                fm = board.fullmove_number
                cp_before = prev if me == chess.WHITE else -prev
                ev = parse_eval(node.comment, mover == chess.WHITE)
                cp_after = None if ev is None else (
                    ev if me == chess.WHITE else -ev)

                if mover == me:
                    if cp_after is not None:
                        b = band_of(fm)
                        r["bn_" + b] += 1
                        if (cp_before - cp_after) >= 200:
                            r["bl_" + b] += 1
                        r["wploss_sum"] += max(
                            0.0, winprob(cp_before) - winprob(cp_after))
                        r["wploss_n"] += 1
                    if fm > 12 and npm(board, "light") > 14:
                        r["peak"] = max(r["peak"], cp_before)
                        if cp_before >= 150:
                            r["eligible"] += 1
                            row = probe(board, move, node, me, cp_before,
                                        game, ply, stats)
                            if row:
                                r["hits"] += 1
                                if row["wp_error"] >= FLOOR:
                                    r["floored"] += 1
                board.push(move)
                prev = ev if ev is not None else prev

            r["post"] = (r["my_elo"] or 0) + r["rdiff"]
            rows.append(r)
    rows.sort(key=lambda x: (x["date"], x["time"]))
    return rows


def gate(rows):
    """Hard-exit unless the published 2026 figures reproduce."""
    if len(rows) != GATE_2026["games"]:
        print("gate: input is not the 1,515-game 2026 corpus — skipping.\n")
        return
    ok = True

    def chk(name, got, want, tol=0.0):
        nonlocal ok
        good = abs(got - want) <= tol
        ok = ok and good
        print("  %-40s got %-9s want %-9s %s"
              % (name, round(got, 2), want, "OK" if good else "MISMATCH"))

    t = [r for r in rows if r["tc"] == "180+2"]
    print("Validation gate (published 2026 figures):")
    chk("games", len(rows), GATE_2026["games"])
    for b, key in (("1-12", "b112"), ("13-25", "b1325"), ("26+", "b26")):
        chk("3+2 blunder band %s (%%)" % b,
            100.0 * sum(r["bl_" + b] for r in t) / sum(r["bn_" + b] for r in t),
            GATE_2026[key], 0.01)
    el = sum(r["eligible"] for r in t)
    chk("3+2 eligible moves", el, GATE_2026["el32"])
    chk("3+2 hanging floored (%)",
        100.0 * sum(r["floored"] for r in t) / el, GATE_2026["hang32"], 0.01)
    ela = sum(r["eligible"] for r in rows)
    chk("all-TC eligible moves", ela, GATE_2026["elall"])
    chk("all-TC hanging floored (%)",
        100.0 * sum(r["floored"] for r in rows) / ela, GATE_2026["hangall"], 0.01)
    chk("all-TC raw hits (hanging.py tripwire)",
        sum(r["hits"] for r in rows), GATE_2026["hits"])
    if not ok:
        sys.exit("VALIDATION GATE FAILED — do not trust anything below.")
    print("  gate passed.\n")


def metrics(gs):
    bn = sum(g["bn_13-25"] + g["bn_26+"] for g in gs)
    bl = sum(g["bl_13-25"] + g["bl_26+"] for g in gs)
    bna = sum(g["bn_" + b] for g in gs for b in ("1-12", "13-25", "26+"))
    bla = sum(g["bl_" + b] for g in gs for b in ("1-12", "13-25", "26+"))
    el = sum(g["eligible"] for g in gs)
    wn = sum(g["wploss_n"] for g in gs)
    return dict(games=len(gs),
                score=sum(g["score"] for g in gs) / len(gs),
                opp=st.mean(g["opp_elo"] for g in gs if g["opp_elo"]),
                wploss=sum(g["wploss_sum"] for g in gs) / wn if wn else float("nan"),
                blunder13=bl / bn if bn else float("nan"),
                blunder_all=bla / bna if bna else float("nan"),
                hang=sum(g["floored"] for g in gs) / el if el else float("nan"),
                eligible=el)


def elo_exp(a, b):
    return 1.0 / (1.0 + 10 ** ((b - a) / 400.0))


def rolling_best(seq, k, key):
    """Highest mean of `key` over contiguous k-windows -> (value, start index)."""
    tot = sum(g[key] for g in seq[:k])
    best, bi = tot, 0
    for i in range(k, len(seq)):
        tot += seq[i][key] - seq[i - k][key]
        if tot > best:
            best, bi = tot, i - k + 1
    return best / k, bi


def show(tag, m):
    print("  %-24s n=%-4d score=%.3f oppElo=%-5.0f wp-loss/move=%.4f "
          "blunder13+=%5.2f%% hang=%5.2f%% (%d elig)"
          % (tag, m["games"], m["score"], m["opp"], m["wploss"],
             100 * m["blunder13"], 100 * m["hang"], m["eligible"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pgn")
    ap.add_argument("--window", action="append", required=True,
                    help="START:END, inclusive UTC dates. First is primary.")
    ap.add_argument("--tc", default="180+2")
    ap.add_argument("--until", default=None, help="pool cutoff date")
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--shuffles", type=int, default=20000)
    a = ap.parse_args()

    rows = scan(a.pgn)
    gate(rows)

    pool = [r for r in rows
            if (not a.tc or r["tc"] == a.tc)
            and (not a.until or r["date"] <= a.until)]
    wins = [tuple(w.split(":")) for w in a.window]
    prim = [r for r in pool if wins[0][0] <= r["date"] <= wins[0][1]]
    rest = [r for r in pool if not (wins[0][0] <= r["date"] <= wins[0][1])]
    k = len(prim)
    if k < 20 or k > len(pool) - 20:
        sys.exit("window is %d of %d pool games — too small or too large to test"
                 % (k, len(pool)))

    print("Pool: tc=%s through %s -> %d games (%s .. %s)"
          % (a.tc or "any", a.until or "end", len(pool),
             pool[0]["date"], pool[-1]["date"]))
    peak = max(pool, key=lambda r: r["post"])
    print("Rating peak in pool: %d on %s\n" % (peak["post"], peak["date"]))

    print("=== Descriptives ===")
    for i, (s, e) in enumerate(wins):
        gs = [r for r in pool if s <= r["date"] <= e]
        show("%s..%s%s" % (s, e, "  (primary)" if i == 0 else ""), metrics(gs))
    show("rest of pool", metrics(rest))
    show("whole pool", metrics(pool))

    print("\n=== Elo over/under-performance ===")
    for tag, gs in ([("%s..%s" % w, [r for r in pool if w[0] <= r["date"] <= w[1]])
                     for w in wins] + [("rest", rest), ("pool", pool)]):
        exp = st.mean(elo_exp(g["my_elo"], g["opp_elo"]) for g in gs
                      if g["my_elo"] and g["opp_elo"])
        act = st.mean(g["score"] for g in gs)
        se = st.pstdev([g["score"] for g in gs]) / len(gs) ** 0.5
        print("  %-24s actual %.3f  Elo-expected %.3f  diff %+.3f "
              "(%.1f SE)  net rating %+d"
              % (tag, act, exp, act - exp, (act - exp) / se if se else 0,
                 sum(g["rdiff"] for g in gs)))

    obs_best, bi = rolling_best(pool, k, "score")
    bw = pool[bi:bi + k]
    print("\nBest %d-game score window in the real data: %s..%s at %.3f"
          % (k, bw[0]["date"], bw[-1]["date"], obs_best))
    show("that window", metrics(bw))

    # ---------------- T1 ----------------
    rng = random.Random(a.seed)
    nulls = []
    for _ in range(a.shuffles):
        sh = pool[:]
        rng.shuffle(sh)
        nulls.append(rolling_best(sh, k, "score")[0])
    p1 = (sum(1 for v in nulls if v >= obs_best) + 1) / (a.shuffles + 1)
    print("\n=== T1: was the streak itself extreme? ===")
    print("  observed best %.4f | shuffled best: mean %.4f, 95th pct %.4f | p = %.3f"
          % (obs_best, st.mean(nulls), sorted(nulls)[int(0.95 * a.shuffles)], p1))

    # ---------------- T2 ----------------
    keys = ("wploss", "blunder13", "blunder_all", "hang")
    obs_p, obs_b = metrics(prim), metrics(bw)
    acc = {kk: [] for kk in keys}
    rng = random.Random(a.seed)
    n2 = max(1000, a.shuffles // 4)
    for _ in range(n2):
        sh = pool[:]
        rng.shuffle(sh)
        m = metrics(sh[rolling_best(sh, k, "score")[1]:][:k])
        for kk in keys:
            acc[kk].append(m[kk])
    print("\n=== T2: selection-aware quality test (HEADLINE, %d shuffles) ==="
          % n2)
    print("  Null: constant skill, games exchangeable. Each shuffle re-runs the "
          "same cherry-pick\n  (hottest %d-game window) and measures that "
          "window's quality. Lower = better play." % k)
    print("  %-12s %9s %9s %10s %10s %8s %8s %10s"
          % ("metric", "primary", "best-win", "null mean", "null p5",
             "p(prim)", "p(best)", "detect@80%"))
    for kk in keys:
        v = sorted(acc[kk])
        sd = st.pstdev(v)
        print("  %-12s %9.4f %9.4f %10.4f %10.4f %8.3f %8.3f %10.4f"
              % (kk, obs_p[kk], obs_b[kk], st.mean(v), v[int(0.05 * len(v))],
                 (sum(1 for x in v if x <= obs_p[kk]) + 1) / (len(v) + 1),
                 (sum(1 for x in v if x <= obs_b[kk]) + 1) / (len(v) + 1),
                 2.8 * sd))
    print("  detect@80%: smallest true improvement this test would catch "
          "4 times in 5.")

    # ---------------- T3 ----------------
    print("\n=== T3: naive window-vs-rest (BIASED — contrast only) ===")
    mp, mr = metrics(prim), metrics(rest)
    obs = {kk: mp[kk] - mr[kk] for kk in keys}
    cnt = {kk: 0 for kk in keys}
    rng = random.Random(a.seed)
    for _ in range(n2):
        sh = pool[:]
        rng.shuffle(sh)
        x, y = metrics(sh[:k]), metrics(sh[k:])
        for kk in keys:
            if abs(x[kk] - y[kk]) >= abs(obs[kk]):
                cnt[kk] += 1
    for kk in keys:
        print("  %-12s primary - rest = %+.4f   two-sided p = %.3f"
              % (kk, obs[kk], (cnt[kk] + 1) / (n2 + 1)))
    print("\nT3 is listed so the bias is visible, not so it can be quoted. "
          "Read T2.")


if __name__ == "__main__":
    main()
