#!/usr/bin/env python3
"""trades/analyze — tables for the "trades from level positions" write-up
(2026-11-25, exploratory, not pre-registered).

    python3 analyze.py TRADES.csv.gz [D18.jsonl.gz]

Input from extract.py. Level = bal == 0 except the clock section (|bal| <= 1).
Error on the move = win-prob lost >= 0.05 (e05), depth 12, Lichess curve
(about half a pawn near equality). Opponents = the same games' other player,
so they face the same openings from the other side.

Rates are standardized to Justin's eval-band mix within each cell (bands on
cp_before: <= -150, -150..-50, -50..50, 50..150, >= 150), so a side that trades
more often from worse positions is not penalized for it. Intervals: game
bootstrap, 2,000 draws, seed 23, me and opponent resampled jointly by game.
DiD = (me - opp on trades) - (me - opp on declines): the part of his gap that
is specific to trading rather than his general error gap in that cell.
"""
import sys, json, gzip
import numpy as np, pandas as pd
import statsmodels.formula.api as smf

B, SEED = 2000, 23
BANDS = [-1e9, -150, -50, 50, 150, 1e9]


def load(p):
    d = pd.read_csv(p, dtype={"gid": str})
    d["e05"] = (d.wp_err >= 0.05).astype(float)
    d["band"] = pd.cut(d.cp_before, BANDS, labels=False)
    d["late"] = np.where(d.phase == "opening", "opening (moves 1-12)", "after move 12")
    return d


def cellstats(d, W):
    """d: rows of one cell. Returns per-game arrays for (mine, took, band) sums/counts."""
    gids = d.gid.unique()
    gi = pd.Series(np.arange(len(gids)), index=gids)
    S = np.zeros((len(gids), 2, 2, 5)); N = np.zeros_like(S)
    idx = (gi[d.gid].to_numpy(), d.mine.to_numpy(int), d.took.to_numpy(int), d.band.to_numpy(int))
    np.add.at(S, idx, d.e05.to_numpy()); np.add.at(N, idx, 1)
    return S, N


def std(S, N, W):
    r = S / np.maximum(N, 1)
    w = np.where(N > 0, W, 0)  # renormalize when a band is empty
    return (r * w).sum(-1) / np.maximum(w.sum(-1), 1e-9) * 100


def compare(d, rng, label):
    W = np.bincount(d[d.mine == 1].band, minlength=5) / (d.mine == 1).sum()
    S, N = cellstats(d, W)
    pt = std(S.sum(0), N.sum(0), W)               # [mine, took]
    idx = rng.integers(0, S.shape[0], (B, S.shape[0]))
    bs = std(S[idx].sum(1), N[idx].sum(1), W)      # [B, mine, took]
    gap_t = bs[:, 1, 1] - bs[:, 0, 1]; gap_d = bs[:, 1, 0] - bs[:, 0, 0]
    ci = lambda a: "[%+.1f, %+.1f]" % tuple(np.percentile(a, [2.5, 97.5]))
    tk = d.groupby("mine").took.mean()
    nt = N.sum(0)[:, 1].sum(-1)
    return {"cell": label, "games": d.gid.nunique(), "my trades": int(nt[1]), "opp trades": int(nt[0]),
            "take% me": round(tk.get(1, np.nan) * 100, 1), "take% opp": round(tk.get(0, np.nan) * 100, 1),
            "trade err me": round(pt[1, 1], 1), "trade err opp": round(pt[0, 1], 1),
            "gap": "%+.1f %s" % (pt[1, 1] - pt[0, 1], ci(gap_t)),
            "decline err me": round(pt[1, 0], 1), "decline err opp": round(pt[0, 0], 1),
            "DiD": "%+.1f %s" % ((pt[1, 1] - pt[0, 1]) - (pt[1, 0] - pt[0, 0]), ci(gap_t - gap_d))}


def show(rows, title):
    print("\n## " + title)
    print(pd.DataFrame(rows).to_string(index=False))


def main(p, d18=None):
    d = load(p)
    rng = np.random.default_rng(SEED)
    L = d[d.bal == 0]
    print("level decision points %d in %d games (me %d / opp %d); trades taken me %d / opp %d" % (
        len(L), L.gid.nunique(), (L.mine == 1).sum(), (L.mine == 0).sum(),
        L[(L.mine == 1)].took.sum(), L[(L.mine == 0)].took.sum()))

    show([compare(L[L.late == ph], rng, ph) for ph in ["opening (moves 1-12)", "after move 12"]],
         "1. All families, by phase")
    rows = []
    for fam in ["Caro", "London", "Englund"]:
        for ph in ["opening (moves 1-12)", "after move 12"]:
            rows.append(compare(L[(L.fam == fam) & (L.late == ph)], rng, f"{fam}, {ph}"))
    show(rows, "2. By repertoire family and phase")
    rows = []
    for c in ["Advance", "Exchange", "Caro-other"]:
        for ph in ["opening (moves 1-12)", "after move 12"]:
            rows.append(compare(L[(L.caro == c) & (L.late == ph)], rng, f"Caro {c}, {ph}"))
    show(rows, "3. Caro by line")

    # piece pairs, after move 12, trades only (no decline comparison possible per pair)
    T = L[(L.took == 1) & (L.late == "after move 12")]
    print("\n## 4. Trades after move 12 by what was traded (raw e05 %, not standardized)")
    t = T.groupby(["fam", "trade_type", "mine"]).e05.agg(["size", "mean"]).unstack("mine")
    t.columns = ["n opp", "n me", "err opp", "err me"]
    t[["err opp", "err me"]] = (t[["err opp", "err me"]] * 100).round(1)
    print(t[(t["n me"] >= 25)].to_string())

    # band: who trades from where
    print("\n## 5. Take rate by eval band (level material, after move 12)")
    A = L[L.late == "after move 12"]
    lab = {0: "clearly worse", 1: "slightly worse", 2: "even", 3: "slightly better", 4: "clearly better"}
    t = A.groupby(["band", "mine"]).agg(n=("took", "size"), take=("took", "mean"), err_take=("e05", lambda s: s[A.loc[s.index, "took"] == 1].mean())).unstack("mine")
    t.index = [lab[i] for i in t.index]
    print((t * [1, 1, 100, 100, 100, 100]).round(1).to_string())

    print("\n## 5b. Trade vs decline, and me vs opp, within each eval band (after move 12)")
    print("err = share of moves losing >= T win-prob; intervals game bootstrap")
    for thr in (0.05, 0.10):
        A2 = A.assign(e=(A.wp_err >= thr).astype(float))
        for fam in (None, "Caro", "London"):
            Z = A2 if fam is None else A2[A2.fam == fam]
            for bnd in range(5):
                z = Z[Z.band == bnd]
                gids = z.gid.unique(); gi = pd.Series(np.arange(len(gids)), index=gids)
                S = np.zeros((len(gids), 2, 2)); N = np.zeros_like(S)
                ix = (gi[z.gid].to_numpy(), z.mine.to_numpy(int), z.took.to_numpy(int))
                np.add.at(S, ix, z.e.to_numpy()); np.add.at(N, ix, 1)
                r = lambda s, n: s / np.maximum(n, 1) * 100
                pt = r(S.sum(0), N.sum(0))
                bi = rng.integers(0, len(gids), (B, len(gids)))
                bs = r(S[bi].sum(1), N[bi].sum(1))
                ci = lambda a: "[%+.1f, %+.1f]" % tuple(np.percentile(a, [2.5, 97.5]))
                print(f"T={thr:.2f} {fam or 'all':6s} {lab[bnd]:15s} my trades {int(N.sum(0)[1,1]):4d}: err {pt[1,1]:5.1f} "
                      f"(my declines {pt[1,0]:5.1f}; trade-decline {pt[1,1]-pt[1,0]:+.1f} {ci(bs[:,1,1]-bs[:,1,0])})  "
                      f"opp trades {pt[0,1]:5.1f} (opp declines {pt[0,0]:5.1f}); me-opp on trades {pt[1,1]-pt[0,1]:+.1f} {ci(bs[:,1,1]-bs[:,0,1])}")

    # clock
    print("\n## 6. Low clock: does trading change the next 10 moves? (|bal| <= 1, after move 12)")
    x = d[(d.phase != "opening") & d.clock_before.notna() & (d.f_moves >= 5)].copy()
    x["clk"] = pd.cut(x.clock_before, [-1, 20, 40, 75, 1e9], labels=["<=20s", "21-40s", "41-75s", ">75s"])
    x["fr"] = x.f_e10 / x.f_moves
    for mine, who in [(1, "me"), (0, "opp")]:
        for c in ["<=20s", "21-40s", "41-75s", ">75s"]:
            z = x[(x.mine == mine) & (x.clk == c)]
            g = pd.factorize(z.gid)[0]
            m = smf.wls("fr ~ took + C(band) + npm_light + bal + C(tc)", z, weights=z.f_moves).fit(cov_type="cluster", cov_kwds={"groups": g})
            m2 = smf.ols("e05 ~ took + C(band) + npm_light + bal + C(tc)", z).fit(cov_type="cluster", cov_kwds={"groups": g})
            lo, hi = m.conf_int().loc["took"]; lo2, hi2 = m2.conf_int().loc["took"]
            print(f"{who:3s} {c:7s} n={len(z):5d} games={z.gid.nunique():4d} take={z.took.mean()*100:4.0f}%  "
                  f"later errors/100 moves if traded {m.params.took*100:+.1f} [{lo*100:+.1f}, {hi*100:+.1f}] (base {z[z.took==0].fr.mean()*100:.1f})  "
                  f"this move err {m2.params.took*100:+.1f} [{lo2*100:+.1f}, {hi2*100:+.1f}]")

    if d18:
        print("\n## 7. Depth-18 re-check of trades after move 12 (deep.py; Stockfish 16, depth 18)")
        r = pd.DataFrame([json.loads(l) for l in gzip.open(d18, "rt")])
        r["e18"] = (r.loss18 >= 0.05).astype(float); r["e12"] = (r.wp_err >= 0.05).astype(float)
        r["better18"] = np.where(r.cp18_before >= 150, "clearly better (d18)", "not clearly better (d18)")
        print(r.groupby(["cell", "mine"]).agg(n=("e18", "size"), err12=("e12", "mean"), err18=("e18", "mean"),
              mean_loss18=("loss18", "mean")).round(3).to_string())
        print("depth-12 flags confirmed at depth 18: %.0f%% (n=%d); depth-18 flags that depth 12 also flagged: %.0f%%" % (
            r[r.e12 == 1].e18.mean() * 100, int(r.e12.sum()), r[r.e18 == 1].e12.mean() * 100))
        for lab2, z in r.groupby("better18"):
            gids = z.gid.unique(); gi = pd.Series(np.arange(len(gids)), index=gids)
            S = np.zeros((len(gids), 2)); N = np.zeros_like(S)
            ix = (gi[z.gid].to_numpy(), z.mine.to_numpy(int))
            np.add.at(S, ix, z.e18.to_numpy()); np.add.at(N, ix, 1)
            bi = rng.integers(0, len(gids), (B, len(gids)))
            bs = S[bi].sum(1) / N[bi].sum(1)
            pt = S.sum(0) / N.sum(0)
            lo, hi = np.percentile(bs[:, 1] - bs[:, 0], [2.5, 97.5]) * 100
            print(f"{lab2:26s} my trades {int(N.sum(0)[1])} err18 {pt[1]*100:.1f}%  opp {int(N.sum(0)[0])} err18 {pt[0]*100:.1f}%  "
                  f"me-opp {(pt[1]-pt[0])*100:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main(*sys.argv[1:])
