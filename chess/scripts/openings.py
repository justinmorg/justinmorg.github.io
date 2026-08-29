#!/usr/bin/env python3
"""
openings.py -- recover the played opening book from move times.

No evals needed. The whole method rests on one observation: a move you have
prepared is played in ~1.4s, and the first move you have not is played in
~2.6s. Feed it PGN with [%clk] on every ply and it reconstructs the repertoire
tree, marks which nodes are book, and flags where the book stops.

Usage
-----
    python3 chess/scripts/openings.py LABEL=file.pgn [LABEL=file.pgn ...] \
        --since 2025-08-29 --tc 180+2,300+0 --min-reps 25

    # add an engine audit of the book moves themselves
    python3 chess/scripts/openings.py ... --engine /home/claude/sf/x/usr/games/stockfish \
        --engine-depth 20 --engine-top 120

Bare paths work too; the label defaults to the filename stem.

Flags
-----
    --tc          comma-separated list, like outcomes.py/features.py (NOT
                  longitudinal.py's single value).  Default 180+2,300+0.
    --since/--until   UTCDate bounds, inclusive, YYYY-MM-DD.
    --user        player name.  Also read from CHESS_USER.  Default jamorgan.
    --user-map    LABEL=name overrides, for chess.com blocks.
    --min-reps    node reps required before a node is judged.  Default 25.
    --max-ply     plies parsed per game.  Default 40.
    --engine      path to a UCI engine; enables the book-move audit.
    --no-gate     skip the validation gate.  Do not use without a reason.

Validation gate
---------------
Clock arithmetic is the one thing here that can be silently wrong, so the
script re-derives two published README figures before doing anything else:
mean seconds per own move at moves 16-20 in the 2026 corpus, which is 8.37s at
180+2 and 7.78s at 300+0 (the README quotes these as 8.4 and 7.8).  Mismatch is
a hard exit.

Book definition (descriptive, not a hypothesis test)
----------------------------------------------------
A node is a position where it is the player's move, keyed by (colour, EPD).
Keying by colour is required: 1.d4 e5 arises both when he plays the Englund and
when an opponent plays it against him, and pooling the two corrupts every share
in the Englund lines.

    book node  ==  reps >= min-reps  and  top-move share >= 0.90
                   and  mean seconds on the top move < 3.0

    gap node   ==  reps >= min-reps  and  not a book node

Both thresholds are conventions.  The 0.90 is arbitrary; the 3.0s is not, and
sits just above twice the in-book mean.
"""

import argparse
import chess
import chess.engine
import chess.pgn
import gzip
import io
import os
import re
import statistics as st
import sys
from collections import defaultdict, Counter

CLK = re.compile(r"\[%clk (\d+):(\d+):(\d+)\]")

GATE_FILE = "jamorgan_blitz_2026_analyzed.pgn.gz"
GATE_EXPECT = {"180+2": 8.37, "300+0": 7.78}
GATE_TOL = 0.05


# ---------------------------------------------------------------- parsing


def opener(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def parse(path, user, tc_set, since, until, max_ply):
    """Yield dicts of games for `user`, with per-ply seconds spent.

    Lichess writes the *initial* clock for ply 1 and ply 2 regardless of what
    was actually spent, and only starts applying the increment from ply 3.  So
    increment is added from ply 3 on, and plies 1-2 carry a spend of ~0 by
    construction rather than by measurement.  Do not read anything into them.
    """
    with opener(path) as fh:
        while True:
            g = chess.pgn.read_game(fh)
            if g is None:
                break
            h = g.headers
            if h.get("Event", "") != "rated blitz game":
                continue
            tc = h.get("TimeControl", "")
            if tc_set and tc not in tc_set:
                continue
            date = h.get("UTCDate", h.get("Date", "")).replace(".", "-")
            if since and date < since:
                continue
            if until and date > until:
                continue
            if h.get("White") == user:
                col = 0
            elif h.get("Black") == user:
                col = 1
            else:
                continue
            base, inc = (int(x) for x in tc.split("+"))
            mycol = chess.WHITE if col == 0 else chess.BLACK
            board = g.board()
            prev = {chess.WHITE: base, chess.BLACK: base}
            seq = []
            n = 0
            for node in g.mainline():
                turn = board.turn
                m = CLK.search(node.comment or "")
                spent = None
                n += 1
                if m:
                    clk = (int(m.group(1)) * 3600 + int(m.group(2)) * 60
                           + int(m.group(3)))
                    spent = prev[turn] - clk + (inc if n > 2 else 0)
                    prev[turn] = clk
                seq.append((board.san(node.move), spent))
                board.push(node.move)
                if n >= max_ply:
                    break
            yield dict(gid=h.get("GameId", "") or h.get("Site", "").rsplit("/", 1)[-1],
                       date=date, tc=tc, col=col, seq=seq,
                       eco=h.get("ECO", ""), op=h.get("Opening", ""),
                       res=h.get("Result", ""))


# ---------------------------------------------------------------- gate


def gate(data_dir):
    path = os.path.join(data_dir, GATE_FILE)
    if not os.path.exists(path):
        sys.exit("GATE FAIL: %s not found; pass --no-gate only if you know why"
                 % path)
    acc = defaultdict(list)
    for g in parse(path, "jamorgan", {"180+2", "300+0"}, None, None, 60):
        mycol = chess.WHITE if g["col"] == 0 else chess.BLACK
        b = chess.Board()
        for i, (san, sp) in enumerate(g["seq"], start=1):
            if b.turn == mycol and sp is not None and 16 <= (i + 1) // 2 <= 20:
                acc[g["tc"]].append(sp)
            b.push(b.parse_san(san))
    bad = []
    for tc, want in GATE_EXPECT.items():
        got = sum(acc[tc]) / len(acc[tc])
        ok = abs(got - want) <= GATE_TOL
        print("  gate %-7s moves 16-20 mean %.2fs (expect %.2f)  %s"
              % (tc, got, want, "ok" if ok else "MISMATCH"))
        if not ok:
            bad.append(tc)
    if bad:
        sys.exit("GATE FAIL: clock arithmetic does not reproduce published "
                 "figures for %s. Every number below would be wrong. Stopping."
                 % ", ".join(bad))


# ---------------------------------------------------------------- tree


class Tree:
    def __init__(self):
        # (col, epd) -> [reps, {san: [count, [my_secs]]}, representative_line]
        # (col, epd) -> [reps, {san: [count, [my_secs]]}, line, ply]
        self.nd = defaultdict(lambda: [0, defaultdict(lambda: [0, []]), None, 0])
        self.games = []

    def add(self, g):
        self.games.append(g)
        b = chess.Board()
        mycol = chess.WHITE if g["col"] == 0 else chess.BLACK
        for i, (san, sp) in enumerate(g["seq"]):
            k = (g["col"], b.epd())
            node = self.nd[k]
            node[0] += 1
            c = node[1][san]
            c[0] += 1
            if b.turn == mycol:
                # plies 1-2 carry no real measurement; see parse()
                if sp is not None and i > 1:
                    c[1].append(sp)
                if node[2] is None:
                    node[2] = line_str(g["seq"][:i])
                    node[3] = i
            b.push(b.parse_san(san))

    def summary(self, k):
        reps, ch, line, ply = self.nd[k]
        items = sorted(ch.items(), key=lambda kv: -kv[1][0])
        san, (cnt, secs) = items[0]
        return dict(reps=reps, line=line, san=san, share=cnt / reps,
                    med=st.median(secs) if secs else None,
                    mean=sum(secs) / len(secs) if secs else None,
                    alts=len(items), ply=ply,
                    others=[(s, v[0]) for s, v in items[1:5]])


def line_str(seq):
    return " ".join(("%d." % (i // 2 + 1) if i % 2 == 0 else "") + m
                    for i, (m, _) in enumerate(seq))


def is_book(s, min_reps, share_min=0.90, sec_max=3.0):
    """Plies 1-2 are time-exempt: Lichess reports no usable spend for them
    (see parse()), so they are judged on share alone."""
    if s["reps"] < min_reps or s["share"] < share_min:
        return False
    if s["ply"] < 2:
        return True
    return s["mean"] is not None and s["mean"] < sec_max


# ---------------------------------------------------------------- reports


def report_first_moves(tree):
    print("\n" + "=" * 78)
    print("FIRST-MOVE ADHERENCE")
    print("=" * 78)
    w = Counter(g["seq"][0][0] for g in tree.games if g["col"] == 0)
    tot = sum(w.values())
    print("as White (n=%d): " % tot
          + ", ".join("%s %d (%.1f%%)" % (m, c, 100 * c / tot)
                      for m, c in w.most_common(4)))
    opp = Counter()
    rep = defaultdict(Counter)
    for g in tree.games:
        if g["col"] != 1:
            continue
        opp[g["seq"][0][0]] += 1
        if len(g["seq"]) > 1:
            rep[g["seq"][0][0]][g["seq"][1][0]] += 1
    tot = sum(opp.values())
    print("as Black (n=%d):" % tot)
    for m, c in opp.most_common(14):
        top = rep[m].most_common(3)
        share = top[0][1] / c if top else 0
        flag = "        " if share >= 0.90 else "  UNPREP"
        print("  1.%-4s %4d %5.1f%%%s  replies: %s"
              % (m, c, 100 * c / tot, flag,
                 ", ".join("%s %d" % (a, b) for a, b in top)))


def report_nodes(tree, min_reps):
    book, gaps = [], []
    for k in tree.nd:
        s = tree.summary(k)
        if s["line"] is None or s["reps"] < min_reps:
            continue
        if s["mean"] is None and s["ply"] >= 2:
            continue
        s["col"] = "W" if k[0] == 0 else "B"
        s["key"] = k
        (book if is_book(s, min_reps) else gaps).append(s)
    for rows, title in ((book, "BOOK NODES"), (gaps, "GAPS")):
        print("\n" + "=" * 78)
        print("%s (>= %d reps)" % (title, min_reps))
        print("=" * 78)
        print("%4s %6s %5s %4s  %s" % ("n", "share", "mean", "col", "line -> move"))
        for s in sorted(rows, key=lambda r: -r["reps"]):
            alt = ("   also: " + ", ".join("%s(%d)" % t for t in s["others"])
                   if s["others"] else "")
            print("%4d %6.2f %5s  %-3s  %s -> %s%s"
                  % (s["reps"], s["share"],
                     "-" if s["mean"] is None else "%.2f" % s["mean"],
                     s["col"], s["line"], s["san"], alt))
    return book, gaps


def report_depth(tree, min_reps):
    """Book depth = consecutive own moves from move 1 that are book moves."""
    fam = defaultdict(list)
    intime, outtime = [], []
    for g in tree.games:
        b = chess.Board()
        mycol = chess.WHITE if g["col"] == 0 else chess.BLACK
        depth, done = 0, False
        for i, (san, sp) in enumerate(g["seq"]):
            if b.turn == mycol and not done:
                s = tree.summary((g["col"], b.epd()))
                if is_book(s, min_reps) and s["san"] == san:
                    depth += 1
                    if sp is not None and i > 1:
                        intime.append(sp)
                else:
                    done = True
                    if sp is not None and i > 1:
                        outtime.append(sp)
            b.push(b.parse_san(san))
        if g["col"] == 0:
            f = "White 1.d4 " + (g["seq"][1][0] if len(g["seq"]) > 1 else "?")
        else:
            f = "Black vs 1." + g["seq"][0][0]
        fam[f].append(depth)
    print("\n" + "=" * 78)
    print("BOOK DEPTH BY FAMILY")
    print("=" * 78)
    print("%-24s %6s %7s %6s" % ("family", "games", "median", "mean"))
    for f, v in sorted(fam.items(), key=lambda kv: -len(kv[1])):
        if len(v) < 10:
            continue
        print("%-24s %6d %7.1f %6.2f"
              % (f, len(v), st.median(v), sum(v) / len(v)))
    print("\nmean secs, in-book moves          : %.2f  (n=%d)"
          % (sum(intime) / len(intime), len(intime)))
    print("mean secs, first out-of-book move : %.2f  (n=%d)"
          % (sum(outtime) / len(outtime), len(outtime)))


def report_engine(tree, book, gaps, path, depth, top_n):
    """Is the fast, consistent move actually the right move?

    This is the one question move times cannot answer.  A node played in 1.0s
    with 100% share is evidence of preparation, not of correct preparation.
    """
    rows = sorted(book + gaps, key=lambda r: -r["reps"])[:top_n]
    eng = chess.engine.SimpleEngine.popen_uci(path)
    out = []
    try:
        for s in rows:
            b = chess.Board()
            for m in re.sub(r"\d+\.", "", s["line"]).split():
                b.push_san(m)
            info = eng.analyse(b, chess.engine.Limit(depth=depth), multipv=4)
            best = info[0]["pv"][0]
            best_cp = info[0]["score"].pov(b.turn).score(mate_score=10000)
            played = b.parse_san(s["san"])
            got = None
            for pv in info:
                if pv["pv"][0] == played:
                    got = pv["score"].pov(b.turn).score(mate_score=10000)
            if got is None:
                b.push(played)
                r = eng.analyse(b, chess.engine.Limit(depth=depth))
                got = -r["score"].pov(b.turn).score(mate_score=10000)
                b.pop()
            out.append((s, got - best_cp, b.san(best), best_cp, got))
    finally:
        eng.quit()
    print("\n" + "=" * 78)
    print("ENGINE AUDIT OF THE BOOK ITSELF (depth %d, top %d nodes by reps)"
          % (depth, len(out)))
    print("=" * 78)
    print("Cost is centipawns lost vs the engine's first choice, from the")
    print("mover's point of view.  Sorted by reps x cost -- how much the")
    print("habit costs per year, not how bad any single move is.")
    print("%4s %6s %6s %6s  %s" % ("n", "mean_s", "cost", "n*cost", "line"))
    for s, cost, best, bcp, gcp in sorted(
            out, key=lambda r: r[0]["reps"] * min(r[1], 0)):
        if cost >= -15:
            continue
        print("%4d %6s %6d %6d  %s -> %s   (engine: %s)"
              % (s["reps"],
                 "-" if s["mean"] is None else "%.2f" % s["mean"],
                 cost, s["reps"] * cost,
                 s["line"] or "(start)", s["san"], best))
    clean = sum(1 for _, c, *_ in out if c >= -15)
    print("\n%d of %d audited nodes are within 15cp of best." % (clean, len(out)))
    return out


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks", nargs="+")
    ap.add_argument("--tc", default="180+2,300+0")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--user", default=os.environ.get("CHESS_USER", "jamorgan"))
    ap.add_argument("--user-map", nargs="*", default=[])
    ap.add_argument("--min-reps", type=int, default=25)
    ap.add_argument("--max-ply", type=int, default=40)
    ap.add_argument("--engine")
    ap.add_argument("--engine-depth", type=int, default=20)
    ap.add_argument("--engine-top", type=int, default=120)
    ap.add_argument("--data-dir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    ap.add_argument("--no-gate", action="store_true")
    a = ap.parse_args()

    if not a.no_gate:
        print("validation gate:")
        gate(a.data_dir)

    umap = dict(x.split("=", 1) for x in a.user_map)
    tc_set = set(a.tc.split(",")) if a.tc else set()
    tree = Tree()
    print("\nblocks:")
    for spec in a.blocks:
        label, _, path = spec.partition("=")
        if not path:
            path, label = label, os.path.basename(label).split(".")[0]
        user = umap.get(label, a.user)
        n = 0
        for g in parse(path, user, tc_set, a.since, a.until, a.max_ply):
            tree.add(g)
            n += 1
        print("  %-14s %5d games  (%s)" % (label, n, user))
    if not tree.games:
        sys.exit("no games matched -- check --tc, --since and the username")
    dates = sorted(g["date"] for g in tree.games)
    print("  TOTAL          %5d games  %s -> %s"
          % (len(tree.games), dates[0], dates[-1]))
    print("  colours: %d White / %d Black"
          % (sum(1 for g in tree.games if g["col"] == 0),
             sum(1 for g in tree.games if g["col"] == 1)))

    report_first_moves(tree)
    book, gaps = report_nodes(tree, a.min_reps)
    report_depth(tree, a.min_reps)
    if a.engine:
        report_engine(tree, book, gaps, a.engine, a.engine_depth, a.engine_top)


if __name__ == "__main__":
    main()
