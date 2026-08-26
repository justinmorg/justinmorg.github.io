#!/usr/bin/env python3
"""
clockstate.py — is a given bucket of games also a clock problem?

Usage:
    python3 clockstate.py block.pgn [block.pgn ...] [--tc 180+2,300+0]

Buckets games exactly as outcomes.py does (peak >= +200; else by middlegame
trough) and prints, per bucket:

  1. Median clock for both sides at fixed move numbers, and the difference.
     Always split by TimeControl — 3+2 floors via the increment and 5+0 does
     not, so pooling these is the exception the README's time-control section
     warns about.
  2. Own seconds per move by band, comparable to `blockstats.py clock`.
  3. Time-forfeit share.

Respects CHESS_USER via hanging.py.
"""
import sys, re, random, statistics as st
from collections import Counter, defaultdict
import chess, chess.pgn
sys.path.insert(0, "/home/claude/justinmorg.github.io/chess/scripts")
from hanging import USER, npm, parse_eval

random.seed(1729)
CLK = re.compile(r"\[%clk\s+(\d+):(\d+):([\d.]+)\]")
ARGS = sys.argv[1:]
TC_SET = {"180+2", "300+0"}
if "--tc" in ARGS:
    i = ARGS.index("--tc")
    TC_SET = set(ARGS[i + 1].split(","))
    ARGS = ARGS[:i] + ARGS[i + 2:]
if not ARGS:
    sys.exit(__doc__)
BLOCKS = ARGS
PROBES = [15, 20, 25, 30, 35, 40]

def secs(comment):
    m = CLK.search(comment or "")
    if not m: return None
    h, mi, s = m.groups()
    return int(h)*3600 + int(mi)*60 + float(s)

# bucket -> tc -> probe -> list of (my_clk - opp_clk)
diff = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
mine = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
opp  = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
term = defaultdict(Counter)
ngames = defaultdict(Counter)
spend = defaultdict(lambda: defaultdict(list))   # bucket -> band -> sec/move

def band(fm):
    for lo, hi in ((1,5),(6,10),(11,15),(16,20),(21,25),(26,30),(31,35)):
        if lo <= fm <= hi: return f"{lo}-{hi}"
    return None

for b in BLOCKS:
    with open(b) as fh:
        while True:
            g = chess.pgn.read_game(fh)
            if g is None: break
            hw, hb = g.headers.get("White",""), g.headers.get("Black","")
            me = chess.WHITE if USER==hw else (chess.BLACK if USER==hb else None)
            if me is None: continue
            tc = g.headers.get("TimeControl","")
            if tc not in TC_SET: continue

            # first pass: classify
            board, prev, node = g.board(), 0, g
            peak, trough, nel = -10**9, 10**9, 0
            rows = []   # (fm, mover, clk)
            while node.variations:
                node = node.variations[0]
                mover, fm = board.turn, board.fullmove_number
                cp = prev if me==chess.WHITE else -prev
                ev = parse_eval(node.comment, mover==chess.WHITE)
                if mover==me and fm>12 and npm(board,"light")>14:
                    peak=max(peak,cp); trough=min(trough,cp); nel+=1
                rows.append((fm, mover, secs(node.comment)))
                board.push(node.move); prev = ev if ev is not None else prev

            if peak >= 200: bucket = "reached +200"
            elif nel == 0:  bucket = "no eligible"
            elif trough > -200: bucket = "even"
            elif trough > -500: bucket = "losing"
            else: bucket = "lost"

            ngames[bucket][tc] += 1
            tm = (g.headers.get("Termination","?") or "").lower()
            term[bucket]["Time forfeit" if (tm == "time forfeit" or
                                            "won on time" in tm or
                                            "on time" in tm) else "other"] += 1

            # clock at each probe move: last clk of each side at that fullmove
            at = {}
            for fm, mover, c in rows:
                if c is not None: at[(fm, mover)] = c
            for p in PROBES:
                a, o = at.get((p, me)), at.get((p, not me))
                if a is not None and o is not None:
                    diff[bucket][tc][p].append(a - o)
                    mine[bucket][tc][p].append(a)
                    opp[bucket][tc][p].append(o)

            # my spend per move by band
            last = None
            for fm, mover, c in rows:
                if mover != me or c is None: continue
                if last is not None:
                    inc = int(tc.split("+")[1]) if "+" in tc else 0
                    d = last - c + inc
                    bd = band(fm)
                    if bd and 0 <= d <= 60: spend[bucket][bd].append(d)
                last = c

print("games per bucket:", {k: dict(v) for k, v in ngames.items()})
for tc in sorted(TC_SET):
    print(f"\n=== {tc} — median clock at move N (mine / opp / diff), seconds ===")
    print(f"{'bucket':14} " + " ".join(f"{'mv'+str(p):>18}" for p in PROBES))
    for bk in ("reached +200", "even", "losing", "lost"):
        cells = []
        for p in PROBES:
            d = diff[bk][tc][p]
            if len(d) < 20: cells.append("        -         ")
            else:
                cells.append(f"{st.median(mine[bk][tc][p]):5.0f}/{st.median(opp[bk][tc][p]):3.0f}/"
                             f"{st.median(d):+5.0f} n={len(d)}")
        print(f"{bk:14} " + " ".join(f"{c:>18}" for c in cells))

print("\n=== my mean seconds per own move, by band (pooled TC) ===")
bands = ["1-5","6-10","11-15","16-20","21-25","26-30","31-35"]
print(f"{'bucket':14} " + " ".join(f"{b:>8}" for b in bands))
for bk in ("reached +200", "even", "losing", "lost"):
    print(f"{bk:14} " + " ".join(
        f"{st.mean(spend[bk][b]):8.1f}" if len(spend[bk][b]) > 30 else "       -"
        for b in bands))

print("\n=== terminations by bucket ===")
for bk in ("reached +200", "even", "losing", "lost", "no eligible"):
    t = term[bk]; n = sum(t.values())
    print(f"{bk:14} n={n:5d}  time forfeit {t['Time forfeit']:4d} ({100*t['Time forfeit']/n:4.1f}%)")
