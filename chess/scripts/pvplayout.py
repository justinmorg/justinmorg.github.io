#!/usr/bin/env python3
"""Does the quiet punishment cash out as material, or not?

The quiet-punished half of the hot-zone judgment drops (n=143) lose to a
non-forcing reply. Two candidate explanations with different remedies:

  DELAYED TACTIC   the punishment is material, it just arrives on move 3 or 5
                   instead of move 1  -> calculation-DEPTH problem
  POSITIONAL DECAY the eval erodes with material staying level
                   -> convert-a-won-position skill, unrelated to the forcing layer

PRE-SPECIFIED before running:
  From the position immediately after the played move, search depth 16 and walk
  the principal variation up to 10 plies. Material balance from my POV using
  P=100 N=320 B=330 R=500 Q=900. Balance is read at the END of the PV window
  (not the first change) so that a capture-and-recapture nets to zero.

    DELAYED TACTIC := PV ends in mate against me, OR my material balance at the
                      end of the window is >= 150cp worse than immediately
                      after my move.
    POSITIONAL     := otherwise.

  The forcing-punished half (n=187) and the 330 matched controls are run
  identically. Controls give the base rate of "material moves over the next 10
  plies anyway", without which the treatment number means nothing.

  Reported: rate by group, and by pre-move eval band, since P(quiet) rises from
  ~37% at level to 63% above +350 and the two explanations were expected to
  split differently there.

Usage:
    python3 chess/scripts/pvplayout.py /home/claude/features
Needs Stockfish at $STOCKFISH_PATH (default /home/claude/sf/x/usr/games/stockfish).
Writes features/pvplayout.csv. Seeds inherited from forcingtest (control
sampling 1/2) so the control set is identical to the published one.
"""
import os
import sys

import chess
import chess.engine
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forcingtest as FT  # noqa: E402

DEPTH = 16
WINDOW = 10
MAT_THRESH = 150
VAL = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
       chess.ROOK: 500, chess.QUEEN: 900}
RNG = np.random.default_rng(23)


def balance(board, me):
    """material balance in cp from `me`'s point of view"""
    t = 0
    for pt, v in VAL.items():
        t += v * (len(board.pieces(pt, me)) - len(board.pieces(pt, not me)))
    return t


def walk(eng, fen, san):
    board = chess.Board(fen)
    me = board.turn
    board.push(board.parse_san(san))
    b0 = balance(board, me)
    info = eng.analyse(board, chess.engine.Limit(depth=DEPTH))
    pv = info.get("pv", [])[:WINDOW]
    mated = False
    for mv in pv:
        board.push(mv)
        if board.is_checkmate():
            mated = board.turn == me
            break
    b1 = balance(board, me)
    sc = info["score"].pov(me)
    return {"mat_delta": b1 - b0, "pv_len": len(pv), "mated": int(mated),
            "final_cp": sc.score(mate_score=10000)}


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
    limit = int(os.environ.get("PVLIMIT", "0"))
    T, C = FT.build_sets()
    fens = FT.extract(T, C)
    ft = pd.read_csv(os.path.join(d, "forcingtest.csv"), dtype={"gid": str})

    rows = []
    for grp, df in (("T", T), ("C", C)):
        for r in df.itertuples():
            rows.append({"grp": grp, "gid": str(r.gid), "ply": int(r.ply),
                         "cp_before": r.cp_before, "drop_cp": r.drop_cp})
    work = pd.DataFrame(rows)
    work = work.merge(ft[["gid", "ply", "reply_forcing"]], on=["gid", "ply"], how="left")
    if limit:
        work = work.head(limit)

    sf = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
    eng = chess.engine.SimpleEngine.popen_uci(sf)
    eng.configure({"Threads": 1, "Hash": 128})
    out = []
    for i, r in enumerate(work.itertuples(), 1):
        f = fens[f"{r.gid}|{r.ply}"]
        rec = walk(eng, f["fen"], f["san"])
        rec.update({"grp": r.grp, "gid": r.gid, "ply": r.ply,
                    "cp_before": r.cp_before, "drop_cp": r.drop_cp,
                    "reply_forcing": r.reply_forcing})
        out.append(rec)
        if i % 50 == 0:
            print(f"  {i}/{len(work)}", flush=True)
    eng.quit()

    o = pd.DataFrame(out)
    o["tactic"] = ((o.mated == 1) | (o.mat_delta <= -MAT_THRESH)).astype(int)
    o.to_csv(os.path.join(d, "pvplayout.csv"), index=False)
    report(o)


def report(o):
    print(f"\nwindow {WINDOW} plies, depth {DEPTH}, threshold {MAT_THRESH}cp")
    print("\n--- classification by group ---")
    groups = [("T quiet-punished", (o.grp == "T") & (o.reply_forcing == 0)),
              ("T forcing-punished", (o.grp == "T") & (o.reply_forcing == 1)),
              ("C controls", o.grp == "C")]
    for name, mk in groups:
        s = o[mk]
        if not len(s):
            continue
        print(f"  {name:20s} n={len(s):3d}  delayed tactic {100*s.tactic.mean():5.1f}%  "
              f"median mat_delta {s.mat_delta.median():+6.0f}cp  "
              f"mate {int(s.mated.sum())}")

    q = o[(o.grp == "T") & (o.reply_forcing == 0)]
    c = o[o.grp == "C"]
    if len(q) and len(c):
        a, b = q.tactic.values.astype(float), c.tactic.values.astype(float)
        obs = a.mean() - b.mean()
        pool = np.concatenate([a, b])
        dd = np.array([(lambda p: p[:len(a)].mean() - p[len(a):].mean())(
            RNG.permutation(pool)) for _ in range(10000)])
        p = (np.sum(np.abs(dd) >= abs(obs)) + 1) / 10001
        print(f"\n  quiet-punished vs controls: {100*obs:+.1f} pp, "
              f"permutation p = {p:.4f}")

    print("\n--- by pre-move eval band (quiet-punished only) ---")
    if len(q):
        q = q.copy()
        q["eb"] = pd.cut(q.cp_before, [-1e9, 0, 150, 350, 1e9],
                         labels=["<=0", "0-150", "150-350", "350+"])
        print(q.groupby("eb", observed=True)
              .agg(n=("tactic", "size"), tactic=("tactic", "mean"),
                   med_delta=("mat_delta", "median"))
              .assign(tactic=lambda x: (100 * x.tactic).round(0)).to_string())


if __name__ == "__main__":
    main()
