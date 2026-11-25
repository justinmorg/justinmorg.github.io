#!/usr/bin/env python3
"""egtruth/analyze — truth checks and the time map (2026-11-25, exploratory).

    python3 analyze.py rows.csv.gz tb.jsonl eng_close.jsonl [verify.jsonl]

Prints every table quoted in notes/2026-11-25-endgame-truth-and-time.md.
Exploratory, not pre-registered. Intervals: 95% bootstrap over games (2,000
draws, seed 7) on the him-minus-opponent difference.

Definitions
  TB part (<= 7 men): mover result before (win / draw / loss; cursed-win and
    blessed-loss count as draws) and after the move played. TB error = result
    got worse (win->draw, win->loss, draw->loss). keep = number of legal moves
    that keep the result.
  Engine part (> 7 men, depth-12 mover win chance 0.25-0.75): SF17.1 150k-node
    MultiPV-4. gap = win chance of best minus win chance of the move played.
    Error = gap >= 0.15. good = moves among the top 4 within 0.08 of best
    ("4" means four or more).
  d12 error = the corpus definition: wp_before - wp_after >= 0.15 (depth 12).
  spent = own clock before minus after, plus increment; negatives dropped.
"""
import sys, gzip, json, math
import numpy as np, pandas as pd

RANK = {"loss": 0, "draw": 1, "win": 2}
NORM = {"win": "win", "cursed-win": "draw", "draw": "draw", "blessed-loss": "draw", "loss": "loss",
        "maybe-win": "win", "maybe-loss": "loss"}
FLIP = {"win": "loss", "loss": "win", "draw": "draw", "cursed-win": "blessed-loss", "blessed-loss": "cursed-win",
        "maybe-win": "maybe-loss", "maybe-loss": "maybe-win"}


def wp(cp):
    if cp >= 10000:
        return 1.0
    if cp <= -10000:
        return 0.0
    cp = max(-1000, min(1000, cp))
    return 1 / (1 + math.exp(-0.00368208 * cp))


def key(fen):
    return " ".join(fen.split()[:4])


def boot_diff(df, col, groups="gid", n=2000, seed=7):
    """him (mine=1) minus opponents (mine=0) mean of col, game bootstrap."""
    g = df.groupby([groups, "mine"])[col].agg(["sum", "count"]).unstack(fill_value=0)
    s1, c1 = g[("sum", 1)].values, g[("count", 1)].values
    s0, c0 = g[("sum", 0)].values, g[("count", 0)].values
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(g), (n, len(g)))
    d = s1[idx].sum(1) / np.maximum(c1[idx].sum(1), 1) - s0[idx].sum(1) / np.maximum(c0[idx].sum(1), 1)
    est = s1.sum() / max(c1.sum(), 1) - s0.sum() / max(c0.sum(), 1)
    return est, np.percentile(d, 2.5), np.percentile(d, 97.5)


def row(label, df, col, pct=True):
    m1 = df[df.mine == 1][col].mean()
    m0 = df[df.mine == 0][col].mean()
    n1 = (df.mine == 1).sum()
    n0 = (df.mine == 0).sum()
    if min(n1, n0) < 20:
        return "| %s | %d / %d | (too few) | | |" % (label, n1, n0)
    e, lo, hi = boot_diff(df, col)
    f = 100 if pct else 1
    return "| %s | %d / %d | %.1f | %.1f | %+.1f [%+.1f, %+.1f] |" % (label, n1, n0, m1 * f, m0 * f, e * f, lo * f, hi * f)


HDR = "| cut | his / their moves | him | opp | gap [95%] |\n|---|---|---|---|---|"


def main(rows, tbf, engf, verf=None):
    d = pd.read_csv(rows)
    d.loc[d.spent < 0, "spent"] = np.nan
    d["d12err"] = ((d.wp_before - d.wp_after) >= 0.15).astype(float)
    d.loc[d.wp_before.isna() | d.wp_after.isna(), "d12err"] = np.nan

    # ------------------------------------------------------------------ TB
    tb = {}
    for line in open(tbf):
        x = json.loads(line)
        tb[x["k"]] = x
    t = d[d.men <= 7].copy()
    t["k"] = t.fen.map(key)
    t = t[t.k.isin(tb)]
    def tbcols(r):
        x = tb[r.k]
        before = NORM.get(x["cat"])
        mv = x["m"].get(r.uci)
        if before is None or mv is None:
            return pd.Series([None, None, np.nan, np.nan])
        after = NORM.get(FLIP.get(mv[0], ""), None)
        keep = sum(1 for v in x["m"].values() if NORM.get(FLIP.get(v[0], ""), None) == before)
        nlose = sum(1 for v in x["m"].values() if (NORM.get(FLIP.get(v[0], "")) or "draw") != before and
                    RANK.get(NORM.get(FLIP.get(v[0], "")), 1) < RANK[before])
        return pd.Series([before, after, keep, nlose])
    t[["tb_before", "tb_after", "keep", "nworse"]] = t.apply(tbcols, axis=1)
    t = t[t.tb_before.notna() & t.tb_after.notna()]
    t["tberr"] = (t.tb_after.map(RANK) < t.tb_before.map(RANK)).astype(float)
    t["win2draw"] = ((t.tb_before == "win") & (t.tb_after != "win")).astype(float)
    t["draw2loss"] = ((t.tb_before == "draw") & (t.tb_after == "loss")).astype(float)
    print("TB rows:", len(t), " games:", t.gid.nunique(), " by era:", t.groupby("era").size().to_dict())

    print("\n## TB 1. Error rates where an error was possible\n")
    print(HDR)
    W = t[t.tb_before == "win"]
    D = t[(t.tb_before == "draw") & (t.nworse > 0)]
    print(row("winning (tb): let the win go", W, "tberr"))
    print(row("drawn, a losing move exists: lost the draw", D, "tberr"))
    for era in ("plateau", "treat"):
        print(row("winning, %s" % era, W[W.era == era], "tberr"))
        print(row("drawn, %s" % era, D[D.era == era], "tberr"))

    print("\n## TB 2. Winning positions by type and by piece moved\n")
    print(HDR)
    for et, s in W.groupby("etype"):
        if len(s) >= 200:
            print(row(et, s, "tberr"))
    for p, s in W.groupby("piece"):
        if len(s) >= 200:
            print(row("moved: " + p, s, "tberr"))
    print("\n drawn (defending) by type\n")
    print(HDR)
    for et, s in D.groupby("etype"):
        if len(s) >= 150:
            print(row(et, s, "tberr"))
    for p, s in D.groupby("piece"):
        if len(s) >= 150:
            print(row("moved: " + p, s, "tberr"))

    print("\n## TB 3. Only moves vs many good moves (winning positions)\n")
    W = W.copy()
    W["kb"] = pd.cut(W.keep, [0, 1, 3, 6, 99], labels=["1 (only move)", "2-3", "4-6", "7+"])
    D = D.copy()
    D["kb"] = pd.cut(D.keep, [0, 1, 3, 6, 99], labels=["1 (only move)", "2-3", "4-6", "7+"])
    for name, S in (("winning", W), ("drawn, defending", D)):
        print("\n" + name + "\n")
        print("| moves that keep it | his moves | his err | opp err | his median s | opp median s | his mean s | opp mean s |\n|---|---|---|---|---|---|---|---|")
        for kb, s in S.groupby("kb", observed=True):
            a, b = s[s.mine == 1], s[s.mine == 0]
            print("| %s | %d | %.1f%% | %.1f%% | %.0f | %.0f | %.1f | %.1f |" % (
                kb, len(a), a.tberr.mean() * 100, b.tberr.mean() * 100, a.spent.median(), b.spent.median(),
                a.spent.mean(), b.spent.mean()))

    print("\n## TB 4. Depth-12 label against the tablebase (his + opp moves, <= 7 men)\n")
    tt = t[t.d12err.notna()]
    both = ((tt.d12err == 1) & (tt.tberr == 1)).sum()
    print("d12 flags:", int(tt.d12err.sum()), " of which TB errors:", int(both),
          " (%.0f%%)" % (100 * both / max(tt.d12err.sum(), 1)))
    print("TB errors:", int(tt.tberr.sum()), " of which d12 flagged:", int(both),
          " (%.0f%%)" % (100 * both / max(tt.tberr.sum(), 1)))

    print("\n## TB 5. Game level: first time a side reaches a TB win on its own move\n")
    first = t[t.tb_before == "win"].sort_values("ply").groupby(["gid", "mine"]).head(1)
    print("| | games | converted (won) | drawn | lost |\n|---|---|---|---|---|")
    for mine, s in first.groupby("mine"):
        print("| %s | %d | %.1f%% | %.1f%% | %.1f%% |" % ("him" if mine else "opp", len(s), 100 * (s.score == 1).mean(),
                                                    100 * (s.score == 0.5).mean(), 100 * (s.score == 0).mean()))
    for era in ("plateau", "treat"):
        f = first[first.era == era]
        print("  %s: him %d games %.1f%% won; opp %d games %.1f%% won" % (
            era, (f.mine == 1).sum(), 100 * (f[f.mine == 1].score == 1).mean(),
            (f.mine == 0).sum(), 100 * (f[f.mine == 0].score == 1).mean()))
    firstd = t[(t.tb_before == "draw") & (t.nworse > 0)].sort_values("ply").groupby(["gid", "mine"]).head(1)
    print("first TB-drawn position with a losing move available: share NOT lost")
    for mine, s in firstd.groupby("mine"):
        print("  %s: %d games, held (draw or win) %.1f%%" % ("him" if mine else "opp", len(s), 100 * (s.score >= 0.5).mean()))
    t.to_csv("/home/claude/eg/tb_rows.csv.gz", index=False)

    # ------------------------------------------------------------------ engine
    e = {}
    for line in open(engf):
        x = json.loads(line)
        e[(x["gid"], x["ply"])] = x
    c = d[(d.men > 7) & d.wp_before.between(0.25, 0.75)].copy()
    c = c[[(g, p) in e for g, p in zip(c.gid, c.ply)]]
    def ecols(r):
        x = e[(r.gid, r.ply)]
        best = wp(x["pv"][0][1])
        pl = wp(x["played"][1])
        good = sum(1 for u, v in x["pv"] if best - wp(v) <= 0.08)
        return pd.Series([best - pl, good, x["depth"] or 0])
    c[["gap", "good", "depth"]] = c.apply(ecols, axis=1)
    c["deeperr"] = (c.gap >= 0.15).astype(float)
    print("\n\nENGINE rows (close, > 7 men):", len(c), " games:", c.gid.nunique(), " median depth:", c.depth.median())
    print("\n## E1. Error rate, close endgames > 7 men\n")
    print(HDR)
    print(row("all (deep engine)", c, "deeperr"))
    print(row("all (depth-12 label)", c[c.d12err.notna()], "d12err"))
    for era in ("plateau", "treat"):
        print(row("deep, " + era, c[c.era == era], "deeperr"))
    for et, s in c.groupby("etype"):
        if len(s) >= 400:
            print(row(et, s, "deeperr"))
    for p, s in c.groupby("piece"):
        print(row("moved: " + p, s, "deeperr"))
    c["haspass"] = (c.passed_mover > 0)
    print(row("mover has a passed pawn", c[c.haspass], "deeperr"))
    print(row("other side has a passed pawn", c[c.passed_other > 0], "deeperr"))
    cc = c[c.d12err.notna()]
    both = ((cc.d12err == 1) & (cc.deeperr == 1)).sum()
    print("\nd12 flags %d, deep agrees %d (%.0f%%); deep errors %d, d12 flagged %d (%.0f%%)" % (
        cc.d12err.sum(), both, 100 * both / cc.d12err.sum(), cc.deeperr.sum(), both, 100 * both / cc.deeperr.sum()))

    print("\n## E2. Time map, close endgames > 7 men\n")
    c["gb"] = c.good.map({1: "1 (only move)", 2: "2-3", 3: "2-3", 4: "4+ (anything sensible)"})
    print("| good moves | share of his moves | his err | opp err | his median s | opp median s | his mean s | opp mean s |\n|---|---|---|---|---|---|---|---|")
    tot = (c.mine == 1).sum()
    for gb, s in c.groupby("gb"):
        a, b = s[s.mine == 1], s[s.mine == 0]
        print("| %s | %.0f%% | %.1f%% | %.1f%% | %.0f | %.0f | %.1f | %.1f |" % (
            gb, 100 * len(a) / tot, a.deeperr.mean() * 100, b.deeperr.mean() * 100, a.spent.median(),
            b.spent.median(), a.spent.mean(), b.spent.mean()))
    print("\nBy clock band (own clock before the move), his moves vs theirs:")
    c["cb"] = pd.cut(c.clock_before, [-1, 10, 20, 40, 90, 999], labels=["<=10s", "11-20s", "21-40s", "41-90s", ">90s"])
    print("| clock | gb | his n | his err | opp err | his mean s | opp mean s |\n|---|---|---|---|---|---|---|")
    for (cb, gb), s in c.groupby(["cb", "gb"], observed=True):
        a, b = s[s.mine == 1], s[s.mine == 0]
        if len(a) < 100:
            continue
        print("| %s | %s | %d | %.1f%% | %.1f%% | %.1f | %.1f |" % (cb, gb, len(a), a.deeperr.mean() * 100,
                                                            b.deeperr.mean() * 100, a.spent.mean(), b.spent.mean()))
    # does extra time on only-moves pay?
    print("\nOnly-move positions: error rate by time spent (his / theirs)")
    om = c[c.good == 1].copy()
    om["sb"] = pd.cut(om.spent, [-1, 2, 5, 10, 999], labels=["0-2s", "3-5s", "6-10s", "11s+"])
    for sb, s in om.groupby("sb", observed=True):
        a, b = s[s.mine == 1], s[s.mine == 0]
        print("  %s: him %d moves %.1f%% | opp %d moves %.1f%%" % (sb, len(a), a.deeperr.mean() * 100, len(b), b.deeperr.mean() * 100))
    many = c[c.good == 4].copy()
    many["sb"] = pd.cut(many.spent, [-1, 2, 5, 10, 999], labels=["0-2s", "3-5s", "6-10s", "11s+"])
    print("Many-good-move positions: share of moves by time spent, and seconds spent per game")
    for mine in (1, 0):
        s = many[many.mine == mine]
        print("  %s: " % ("him" if mine else "opp") + ", ".join("%s %.0f%%" % (k, 100 * v) for k, v in
                                                          s.sb.value_counts(normalize=True).sort_index().items()))
    sec = c.groupby(["gid", "mine", "gb"]).spent.sum().unstack("gb").fillna(0).groupby("mine").mean()
    print("mean seconds per game (close >7-man endgame moves) by good-move class:\n", sec.round(1).to_string())
    print("\n## E4. Where the excess is: good-move class x clock, time spent\n")
    print(HDR)
    for lab, s in [("4+ good, clock <= 20s", c[(c.good == 4) & (c.clock_before <= 20)]),
                   ("4+ good, clock 21-90s", c[(c.good == 4) & c.clock_before.between(21, 90)]),
                   ("4+ good, clock > 90s", c[(c.good == 4) & (c.clock_before > 90)]),
                   ("only move, clock <= 20s", c[(c.good == 1) & (c.clock_before <= 20)]),
                   ("only move, played in 0-2s", c[(c.good == 1) & (c.spent <= 2)]),
                   ("4+ good, played in 0-2s", c[(c.good == 4) & (c.spent <= 2)]),
                   ("4+ good, 3s or more", c[(c.good == 4) & (c.spent > 2)]),
                   ("3+2 only", c[c.tc == "180+2"]), ("5+0 only", c[c.tc == "300+0"])]:
        print(row(lab, s, "deeperr"))
    ex = {}
    for gb, s in c.groupby("gb"):
        a, b = s[s.mine == 1], s[s.mine == 0]
        ex[gb] = len(a) * (a.deeperr.mean() - b.deeperr.mean())
    print("\nexcess errors (his moves x (his rate - opp rate)) by class:", {k: round(v) for k, v in ex.items()},
          "total", round(sum(ex.values())))
    sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), ".."))
    import chess, scanlib
    def free(r):
        b = chess.Board(r.fen)
        b.push_uci(r.uci)
        return int(bool(scanlib.winning_captures(b)))
    e4 = c[(c.good == 4) & (c.deeperr == 1)].copy()
    e4["free"] = e4.apply(free, axis=1)
    e4["low"] = e4.clock_before <= 20
    print("\n4+ good errors that leave a winning capture (scanlib.winning_captures after the move):")
    print(e4.groupby(["low", "mine"]).free.agg(["mean", "count"]).round(3).to_string())
    o = c[(c.good == 4) & (c.deeperr == 0)].sample(3000, random_state=1)
    o["free"] = o.apply(free, axis=1)
    print("baseline, 4+ good non-errors (3,000 sampled):", o.groupby("mine").free.mean().round(3).to_dict())
    print("piece moved in 4+ good errors at clock <= 20s:")
    print(e4[e4.low].groupby("mine").piece.value_counts(normalize=True).round(2).unstack().to_string())
    c.to_csv("/home/claude/eg/eng_rows.csv.gz", index=False)

    if verf:
        v = [json.loads(l) for l in open(verf)]
        vv = pd.DataFrame(v)
        print("\n## E3. Depth-20 verification sample\n")
        for src, s in vv.groupby("src"):
            print(src, "n=%d" % len(s), "confirmed gap>=0.15: %.0f%%" % (100 * (s.gap20 >= 0.15).mean()),
                  "gap>=0.10: %.0f%%" % (100 * (s.gap20 >= 0.10).mean()))
        for (src, mine), s in vv.groupby(["src", "mine"]):
            print("  ", src, "him" if mine else "opp", "n=%d confirmed %.0f%%" % (len(s), 100 * (s.gap20 >= 0.15).mean()))


if __name__ == "__main__":
    main(*sys.argv[1:])
