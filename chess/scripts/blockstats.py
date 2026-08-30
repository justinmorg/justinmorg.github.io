#!/usr/bin/env python3
"""Significance tests across blocks. Reproduces every p-value in the README.

longitudinal.py reports per-block rates with bootstrap CIs. Reading significance
off overlapping CIs is unreliable, and it cannot handle two things this project
kept running into:

  - picking the extreme block *after* looking (the June 2025 dip)
  - unequal block sizes, where rarefaction intervals are meaningless

Both are handled by shuffling labels at the game level, which is what this does.

Subcommands
-----------
shuffle  NAME=FILE [NAME=FILE ...]
    Are these blocks different from each other at all? Shuffles block labels
    across games and asks how often the observed spread (max rate - min rate)
    arises by chance. Also reports how often the *minimum* falls as low as
    observed -- the correct test when a block was singled out for being lowest.

pools    WINDOW:POOL=FILE [...]
    Two pools (e.g. lichess vs chess.com) compared across date-matched windows,
    shuffling pool labels WITHIN each window so period cannot stand in for pool.
    Use this, not a pooled baseline, whenever one side is date-specific: a
    pooled baseline absorbs between-block noise into the contrast and overstates
    the difference. That error turned p = 0.10 into p = 0.031 once already.

clock    NAME=FILE [NAME=FILE ...]
    Mean seconds spent per own move by 5-move band. No evals needed. Only
    compare within one time control.

Metrics for shuffle/pools, in two families that divide by different things:

  per eligible winning-middlegame MOVE (fullmove>12, light npm>14, cp>=+150)
    hang        floored hanging material
    hungself    the 'hung it myself' subset

  per GAME, mirroring outcomes.py's eligibility (no cp gate)
    reached     peak middlegame eval >= +200
    noelig      game has no eligible middlegame move at all
    reached_mg  reached, conditioned on games that had a middlegame

The three game metrics exist so the "Where Q4 2025 lands" table in the README
is reproducible from committed tooling rather than from an ad-hoc groupby.
Do not compare a rate from one family against a rate from the other; they have
different denominators.

--tc takes a comma-separated list (the outcomes.py/features.py convention).
A single value still works. The published Q4 table is a 180+2,300+0 run.
Eligibility mirrors longitudinal.py exactly: own move, fullmove > 12,
npm(board,'light') > 14, eval before the move >= +150cp. Floor is
wp_error >= 0.02.

Examples
--------
    python3 blockstats.py shuffle 2024H2=h2.pgn Q1=q1.pgn Q2=q2.pgn
    python3 blockstats.py pools '2024:li=h2_sep.pgn' '2024:cc=cc_q4.pgn' \\
                                '2026:li=li_26.pgn' '2026:cc=cc_26.pgn'
    python3 blockstats.py clock --tc 180+2 li=corpus.pgn cc=cc_blitz.pgn

CHESS_USER selects the account name per file; for mixed comparisons set it with
the --user flag as NAME=account (see pools example in the README).
"""
import argparse
import collections
import os
import random
import re
import statistics as st
import sys

import chess
import chess.pgn

from hanging import npm, parse_eval, probe

CLK = re.compile(r"\[%clk\s+(\d+):(\d+):([\d.]+)\]")


def parse_tc(tc):
    """None, or a set. Accepts '180+2' and '180+2,300+0' alike."""
    if not tc:
        return None
    return {t.strip() for t in tc.split(",") if t.strip()}


def per_game(path, user, tc=None, need_hits=True):
    """Per game: (eligible, floored_hits, hung_it_myself, n_elig_mg, peak).

    The first three mirror longitudinal.py.  The last two mirror *outcomes.py*
    and are deliberately not the same eligibility: `eligible` here carries the
    `cp_before >= 150` gate that defines a winning-middlegame move, while
    outcomes.py's `n_elig` and `peak` count every own middlegame move
    regardless of eval.  Reusing `eligible` for the reached metrics would
    silently redefine them; keep the two counters separate.

    `need_hits=False` skips the SEE probe entirely, which is the whole cost of
    this pass.  The game-level metrics do not need it.
    """
    stats = {"games": 0, "user_moves": 0, "in_check": 0, "matched": 0}
    rows = []
    n_read = n_matched = 0
    with open(path, errors="replace") as fh:
        while True:
            game = chess.pgn.read_game(fh)
            if game is None:
                break
            if tc and game.headers.get("TimeControl") not in tc:
                continue
            hw, hb = game.headers.get("White", ""), game.headers.get("Black", "")
            if user == hw:
                me = chess.WHITE
            elif user == hb:
                me = chess.BLACK
            else:
                n_read += 1
                continue
            n_read += 1
            n_matched += 1
            board, prev, ply, node = game.board(), 0, 0, game
            elig, hits = 0, []
            n_elig_mg, peak = 0, -10 ** 9
            while node.variations:
                node = node.variations[0]
                move, mover = node.move, board.turn
                ply += 1
                cp_before = prev if me == chess.WHITE else -prev
                ev = parse_eval(node.comment, mover == chess.WHITE)
                light = npm(board, "light")
                if mover == me and board.fullmove_number > 12 and light > 14:
                    # outcomes.py's eligibility: no eval gate
                    n_elig_mg += 1
                    peak = max(peak, cp_before)
                    if cp_before >= 150:
                        elig += 1
                        if need_hits:
                            r = probe(board, move, node, me, cp_before,
                                      game, ply, stats)
                            if r:
                                hits.append(r)
                board.push(move)
                prev = ev if ev is not None else prev
            fl = [r for r in hits if r["wp_error"] >= 0.02]
            rows.append((elig, len(fl),
                         sum(1 for r in fl if r["label"] == "hung it myself"),
                         n_elig_mg, peak))
    # The CHESS_USER silent zero.  The previous version of this guard tested
    # stats["games"], which nothing in this function ever incremented, so it
    # could never fire.  Count locally instead.  This matters more now that
    # need_hits=False skips probe() and leaves `stats` untouched entirely.
    if n_read and not n_matched:
        sys.exit("ERROR: %d games read from %s but none have user %r. "
                 "Set --user or CHESS_USER." % (n_read, path, user))
    return rows


# Metric -> (denominator, numerator) for one game row.
#
# The three move-rate metrics divide by eligible moves.  The three game-rate
# metrics divide by 1 game, and `reached_mg` returns a denominator of 0 for
# games with no middlegame, which drops them from the aggregate exactly as
# conditioning on "games that had a middlegame" should.
MOVE_METRICS = ("hang", "hungself")
GAME_METRICS = ("reached", "noelig", "reached_mg")
ALL_METRICS = MOVE_METRICS + GAME_METRICS


def metric_pair(row, metric):
    elig, fl, hs, n_mg, peak = row
    if metric == "hang":
        return (elig, fl)
    if metric == "hungself":
        return (elig, hs)
    if metric == "reached":
        return (1, 1 if peak >= 200 else 0)
    if metric == "noelig":
        return (1, 1 if n_mg == 0 else 0)
    if metric == "reached_mg":
        return (0, 0) if n_mg == 0 else (1, 1 if peak >= 200 else 0)
    raise ValueError(metric)


def unit_label(metric):
    return "eligible" if metric in MOVE_METRICS else "games in denom"


def rates(labels, pairs):
    a = collections.defaultdict(lambda: [0, 0])
    for lab, (e, x) in zip(labels, pairs):
        a[lab][0] += e
        a[lab][1] += x
    return {k: 100.0 * v[1] / v[0] for k, v in a.items() if v[0]}


def cmd_shuffle(args):
    m = args.metric
    need = m in MOVE_METRICS
    labels, pairs, sizes = [], [], {}
    for spec in args.blocks:
        name, path = spec.split("=", 1)
        rows = per_game(path, args.user, parse_tc(args.tc), need_hits=need)
        sizes[name] = len(rows)
        for r in rows:
            labels.append(name)
            pairs.append(metric_pair(r, m))
    obs = rates(labels, pairs)
    print("metric: %s   (%d games across %d blocks)\n"
          % (m, len(labels), len(sizes)))
    print("%-12s %7s %15s %8s"
          % ("block", "games", unit_label(m), "rate%"))
    for name in sizes:
        e = sum(p[0] for l, p in zip(labels, pairs) if l == name)
        print("%-12s %7d %15d %8.2f" % (name, sizes[name], e, obs[name]))
    spread = max(obs.values()) - min(obs.values())
    lo, hi = min(obs.values()), max(obs.values())
    lo_name = min(obs, key=obs.get)
    hi_name = max(obs, key=obs.get)
    rng = random.Random(args.seed)
    work = list(labels)
    c_spread = c_min = c_max = 0
    for _ in range(args.n):
        rng.shuffle(work)
        r = rates(work, pairs)
        if max(r.values()) - min(r.values()) >= spread:
            c_spread += 1
        if min(r.values()) <= lo:
            c_min += 1
        if max(r.values()) >= hi:
            c_max += 1
    print("\n%d shuffles, seed %d" % (args.n, args.seed))
    print("  spread %.2f pp across blocks        p = %.4f"
          % (spread, (c_spread + 1) / (args.n + 1)))
    print("  minimum block (%s, %.2f%%)  p = %.4f"
          % (lo_name, lo, (c_min + 1) / (args.n + 1)))
    print("  maximum block (%s, %.2f%%)  p = %.4f"
          % (hi_name, hi, (c_max + 1) / (args.n + 1)))
    print("\n  Use the minimum- or maximum-block p when a block was singled\n"
          "  out for being extreme, whichever end it was extreme at; use the\n"
          "  spread p to ask whether any block differs at all.  Quoting the\n"
          "  wrong one is how the June 2025 dip nearly became a finding.")


def cmd_pools(args):
    m = args.metric
    need = m in MOVE_METRICS
    users = dict(u.split("=", 1) for u in args.user_map) if args.user_map else {}
    win = collections.defaultdict(list)
    for spec in args.blocks:
        head, path = spec.split("=", 1)
        window, pool = head.split(":", 1)
        rows = per_game(path, users.get(pool, args.user), parse_tc(args.tc),
                        need_hits=need)
        for r in rows:
            win[window].append((pool, metric_pair(r, m)))
    pools = []
    for v in win.values():
        for p, _ in v:
            if p not in pools:
                pools.append(p)
    if len(pools) != 2:
        sys.exit("pools expects exactly two pool names, got %s" % pools)
    a, b = pools

    def diff(assign):
        agg = collections.defaultdict(lambda: [0, 0])
        for v in assign.values():
            for lab, (e, x) in v:
                agg[lab][0] += e
                agg[lab][1] += x
        return (100.0 * agg[b][1] / agg[b][0]) - (100.0 * agg[a][1] / agg[a][0])

    obs = diff(win)
    print("metric: %s\n" % m)
    print("%-16s %-6s %7s %15s %8s"
          % ("window", "pool", "games", unit_label(m), "rate%"))
    for w, v in win.items():
        for p in pools:
            sub = [x for lab, x in v if lab == p]
            e = sum(s[0] for s in sub)
            n = sum(s[1] for s in sub)
            print("%-16s %-6s %7d %9d %8.2f" % (w, p, len(sub), e, 100.0 * n / e))
    rng = random.Random(args.seed)
    c = 0
    for _ in range(args.n):
        sh = {}
        for w, v in win.items():
            labs = [lab for lab, _ in v]
            rng.shuffle(labs)
            sh[w] = [(labs[i], x) for i, (_, x) in enumerate(v)]
        if abs(diff(sh)) >= abs(obs):
            c += 1
    print("\n%s - %s = %+.2f pp   p = %.4f   (%d perms within window, seed %d)"
          % (b, a, obs, (c + 1) / (args.n + 1), args.n, args.seed))


def cmd_clock(args):
    print("mean seconds per own move, by 5-move band (tc=%s)\n" % args.tc)
    for spec in args.blocks:
        name, path = spec.split("=", 1)
        band = collections.defaultdict(list)
        with open(path, errors="replace") as fh:
            while True:
                g = chess.pgn.read_game(fh)
                if g is None:
                    break
                # cmd_clock is deliberately single-tc: it reads the increment
                # out of the string below, which a list cannot supply.
                if args.tc and g.headers.get("TimeControl") != args.tc:
                    continue
                hw, hb = g.headers.get("White", ""), g.headers.get("Black", "")
                if args.user == hw:
                    off = 0
                elif args.user == hb:
                    off = 1
                else:
                    continue
                inc = 0
                if args.tc and "+" in args.tc:
                    inc = int(args.tc.split("+")[1])
                cl = []
                for node in g.mainline():
                    m = CLK.search(node.comment or "")
                    cl.append(None if not m else
                              int(m.group(1)) * 3600 + int(m.group(2)) * 60
                              + float(m.group(3)))
                mine = cl[off::2]
                for k in range(1, len(mine)):
                    if mine[k] is None or mine[k - 1] is None:
                        continue
                    sp = mine[k - 1] - mine[k] + inc
                    if -1 < sp < 180:
                        band[min(((k + 1) - 1) // 5 * 5 + 1, 56)].append(sp)
        row = "  ".join("%d-%d:%5.1f" % (k, k + 4, st.mean(band[k]))
                        for k in sorted(band) if k <= 41 and len(band[k]) > 30)
        print("  %-10s %s" % (name, row))
    print("\n  Only compare within one time control. 3+2 floors near 18-20s via\n"
          "  increment; 5+0 has no floor. See the README on pooling.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["shuffle", "pools", "clock"])
    ap.add_argument("blocks", nargs="+")
    ap.add_argument("--metric", default="hang", choices=list(ALL_METRICS),
                    help="hang/hungself are per eligible winning-middlegame "
                         "move; reached/noelig/reached_mg are per game")
    ap.add_argument("--tc", default=None,
                    help="comma-separated TimeControl allow-list, "
                         "e.g. 180+2,300+0. A single value still works.")
    ap.add_argument("--n", type=int, default=20000, help="permutations")
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--user", default=os.environ.get("CHESS_USER", "jamorgan"))
    ap.add_argument("--user-map", nargs="*", default=None,
                    help="POOL=account, e.g. li=jamorgan cc=justinmorg")
    a = ap.parse_args()
    {"shuffle": cmd_shuffle, "pools": cmd_pools, "clock": cmd_clock}[a.cmd](a)


if __name__ == "__main__":
    main()
