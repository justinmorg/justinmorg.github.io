#!/usr/bin/env python3
"""
panelrep.py — do panel players use Justin's openings, and what else works for them?

Exploratory, not pre-specified. Reads the raw panel PGNs (raw_2509 + raw_2609,
extracted), panel player's own choices only (the OPP side is anonymous and
one-off). Three contexts, each classified from the panel player's own moves:

    white     London (1.d4 with Bf4 in the first three moves, no c4 before it)
              / other 1.d4 / 1.e4 / 1.Nf3 / 1.c4 / other
    vs 1.e4   Caro / Sicilian / 1...e5 / French / Scandinavian / other
    vs 1.d4   Englund / 1...d5 / 1...Nf6 / other

Outcome: score minus Elo expectation from the game's own rating tags, minus
that player-month's mean (panel players were selected on rating change, so
improvers over-score all month; demeaning stops month mix posing as opening).
"Sometimes" = the player used Justin's family in 5-95% of that context, >= 10
games. Comparison is within player: (alternative over-expectation) minus (his
family over-expectation), only alternatives with >= 10 games for that player,
pooled with harmonic-n weights, 95% interval by bootstrap over players.

Usage:
    python3 panelrep.py RAW_DIR [--min 10]
"""
import glob
import os
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

HDR = re.compile(r'^\[(\w+) "(.*)"\]$')
MINE = {"white": "London", "vs 1.e4": "Caro", "vs 1.d4": "Englund"}


def games(path):
    with open(path) as f:
        h = {}
        for line in f:
            line = line.rstrip("\n")
            m = HDR.match(line)
            if m:
                h[m.group(1)] = m.group(2)
            elif line.startswith("1."):
                yield h, line
                h = {}


def sans(mv):
    t = re.sub(r"\{[^}]*\}", "", mv).split()
    return [x for x in t if not re.match(r"^\d+\.+$", x) and x not in ("1-0", "0-1", "1/2-1/2", "*")]


def classify(color, s):
    if color == "white":
        w = s[0::2][:3]
        if not w:
            return None, None
        if w[0] == "d4":
            if "Bf4" in w and ("c4" not in w or w.index("c4") > w.index("Bf4")):
                return "white", "London"
            return "white", "other 1.d4"
        return "white", {"e4": "1.e4", "Nf3": "1.Nf3", "c4": "1.c4", "e3": "1.e3", "b3": "1.b3",
                         "f4": "1.f4", "g3": "1.g3"}.get(w[0], "other")
    if len(s) < 2:
        return None, None
    if s[0] == "e4":
        return "vs 1.e4", {"c6": "Caro", "c5": "Sicilian", "e5": "1...e5", "e6": "French",
                           "d5": "Scandinavian", "Nc6": "1...Nc6", "g6": "Modern/Pirc",
                           "d6": "Modern/Pirc"}.get(s[1], "other")
    if s[0] == "d4":
        return "vs 1.d4", {"e5": "Englund", "d5": "1...d5", "Nf6": "1...Nf6", "e6": "1...e6",
                           "g6": "1...g6/d6", "d6": "1...g6/d6", "c6": "1...c6", "f5": "Dutch",
                           "Nc6": "1...Nc6"}.get(s[1], "other")
    return None, None


def load(raw):
    rows, seen = [], set()
    for p in sorted(glob.glob(os.path.join(raw, "*.pgn"))):
        pid, month = os.path.basename(p).split("_")[:2]
        for h, mv in games(p):
            if h.get("TimeControl") not in ("180+2", "300+0"):
                continue
            key = (pid, h.get("GameId"))
            if key in seen:
                continue
            seen.add(key)
            color = "white" if h.get("White") == pid else "black" if h.get("Black") == pid else None
            if color is None:
                continue
            res = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(h.get("Result"))
            try:
                we, be = int(h["WhiteElo"]), int(h["BlackElo"])
            except (KeyError, ValueError):
                continue
            if res is None:
                continue
            ctx, fam = classify(color, sans(mv))
            if ctx is None:
                continue
            me, op = (we, be) if color == "white" else (be, we)
            score = res if color == "white" else 1 - res
            exp = 1 / (1 + 10 ** ((op - me) / 400))
            rows.append(dict(pid=pid, month=month, ctx=ctx, fam=fam, elo=me, score=score, over=score - exp))
    d = pd.DataFrame(rows)
    # Panel players were selected on rating change, so many sit far from their
    # rating all month (improvers over-score). Remove each player-month's own
    # mean, so a contrast cannot come from a player using an opening mostly in
    # the month they happened to be improving.
    d["over_raw"] = d.over
    d["over"] = d.over - d.groupby(["pid", "month"]).over.transform("mean")
    return d


def main():
    raw = sys.argv[1]
    mn = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 10
    d = load(raw)
    rng = np.random.default_rng(23)
    print(f"games: {len(d)}  players: {d.pid.nunique()}")
    for ctx, mine in MINE.items():
        c = d[d.ctx == ctx]
        share = c.groupby("pid").fam.apply(lambda f: (f == mine).mean())
        n = c.groupby("pid").size()
        nm = c[c.fam == mine].groupby("pid").size().reindex(share.index, fill_value=0)
        main_ = share[(share > 0.95) & (n >= mn)].index
        some = share[(share >= 0.05) & (share <= 0.95) & (nm >= mn)].index
        anyp = share[nm > 0].index
        print(f"\n==== {ctx}: {mine}")
        print(f"  players with any {mine} game: {len(anyp)} of {share.size};  main weapon (>95%): "
              f"{len(main_)};  sometimes (5-95%, >={mn} games): {len(some)}")
        print("  context mix, all panel players:",
              (c.fam.value_counts(normalize=True) * 100).round(1).to_dict())
        # within-player contrasts
        per = defaultdict(list)  # fam -> list of (diff, weight, n_alt, pid)
        for pid in some:
            g = c[c.pid == pid]
            m = g[g.fam == mine]
            for fam, a in g[g.fam != mine].groupby("fam"):
                if len(a) < mn:
                    continue
                w = 1 / (1 / len(a) + 1 / len(m))
                per[fam].append((a.over.mean() - m.over.mean(), w, len(a), pid))
        mine_over = c[c.pid.isin(some) & (c.fam == mine)].over_raw.mean()
        print(f"  sometimes-players: {mine} {int(nm[some].sum())} games, over-expectation "
              f"{mine_over * 100:+.1f} per 100")
        out = []
        for fam, L in per.items():
            a = np.array([x[0] for x in L]); w = np.array([x[1] for x in L])
            est = (a * w).sum() / w.sum()
            if len(L) >= 3:
                b = [(a[i] * w[i]).sum() / w[i].sum()
                     for i in rng.integers(0, len(L), (4000, len(L)))]
                lo, hi = np.percentile(b, [2.5, 97.5])
            else:
                lo = hi = np.nan
            out.append(dict(alternative=fam, players=len(L), games=sum(x[2] for x in L),
                            vs_mine=est * 100, lo=lo * 100, hi=hi * 100,
                            raw_over=c[c.pid.isin([x[3] for x in L]) & (c.fam == fam)].over_raw.mean() * 100))
        if out:
            print(pd.DataFrame(out).sort_values("vs_mine", ascending=False).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
