#!/usr/bin/env python3
"""Is the hot-zone error a missed forcing move, or a move that loses to one?

The group R reflection notes suggested a hypothesis: the game-deciding move in
a level middlegame is one where a capture or check was available and not seen.
This tests it, and splits it in two — because "forcing move" is ambiguous
between *my* resources and *theirs*:

  H1  the position contained a winning forcing move I failed to find
      -> engine's best move is a capture/check more often in blunders
  H2  my move loses to an immediate forcing reply I failed to check
      -> engine's best reply, after my move, is a capture/check more often

H1 is null and H2 is large. See the README section for the numbers.

Design. Treatment = the permanent hot-zone judgment drops (level at middlegame
entry, first drop permanent, moves 13-25, npm >= 13, hang_label none, quiet
opponent move, not in check), both sites, n = 330.  Control = positions passing
the *same* position filters from the *same* population of games, where the move
played was fine (|drop_cp| <= 30), one per game, sampled to equal n.  Controls
therefore differ from treatment only in the outcome, not in phase, material,
opponent-move type or check state — which is what makes the null on H1
informative rather than merely underpowered.

Two engine searches per position at depth 12: the position itself (best move)
and the position after the played move (best reply).  Depth 12 matches the
corpus annotation depth; --depth16-check re-runs a 60/60 subsample at depth 16,
since a claim about which move is best is exactly the kind of thing the
README's analysis-depth caveat warns about.  Significance by permutation on the
group label, not CI overlap, per project habit.

"Forcing" = `board.is_capture(mv) or board.gives_check(mv)`, python-chess, so
en-passant counts as a capture and discovered checks count as checks.

Caveat kept in view: a >=200cp drop usually *has* to cash out as material, so
part of H2's 57% is mechanical.  The asymmetry is what carries the finding —
own forcing layer is handled well (87% of controls where best is forcing), the
opponent's is not.  Do not quote the 57% alone.

Usage:
    python3 chess/scripts/firstdrop.py /home/claude/features     # prerequisite
    python3 chess/scripts/forcingtest.py [features_dir] [--depth16-check]

Needs the analyzed PGNs in chess/data (FEN + played SAN come from a PGN walk,
since moves.csv.gz stores neither) and Stockfish at $STOCKFISH_PATH, default
/home/claude/sf/x/usr/games/stockfish.  Writes features_dir/forcingtest.csv.
Seeds fixed (control sampling 1/2, permutation 0, subsample 7) so reruns are
identical.
"""
import glob
import gzip
import json
import os
import sys

import chess
import chess.engine
import chess.pgn
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

args = [a for a in sys.argv[1:] if not a.startswith("--")]
FEAT = args[0] if args else "/home/claude/features"
D16 = "--depth16-check" in sys.argv
SF = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")

DEPTH = 12
N_PERM = 10000
CTRL_MAX_DROP = 30


def forcing(board, mv):
    return board.is_capture(mv) or board.gives_check(mv)


def build_sets():
    m = pd.read_csv(os.path.join(FEAT, "moves.csv.gz"), low_memory=False)
    fd = pd.read_csv(os.path.join(FEAT, "firstdrop", "firstdrop_200.csv"))
    lv = pd.read_csv(os.path.join(FEAT, "firstdrop", "level_games.csv"))
    if len(m) != 178684:
        sys.exit(f"ERROR: expected 178,684 own-move rows, got {len(m)} — "
                 f"wrong features run")
    level = set(lv[lv.entry_bucket == "level"].gid)

    T = fd[fd.gid.isin(level) & (fd.rec5 == False)                        # noqa: E712
           & fd.fullmove.between(13, 25) & (fd.npm_light >= 13)
           & (fd.hang_label == "none") & (fd.opp_prev_kind == "quiet")
           & (fd.in_check == 0)]
    if len(T) != 330:
        sys.exit(f"ERROR: treatment set is {len(T)}, expected 330 — "
                 f"selection drifted from the published run")

    pool = m[m.gid.isin(level) & m.fullmove.between(13, 25)
             & (m.npm_light >= 13) & (m.hang_label == "none")
             & (m.opp_prev_kind == "quiet") & (m.in_check == 0)
             & (m.mate_flag == 0) & (m.drop_cp.abs() <= CTRL_MAX_DROP)
             & (~m.gid.isin(set(T.gid)))].copy()
    pool = pool.sample(frac=1, random_state=1).drop_duplicates("gid")
    C = pool.sample(n=len(T), random_state=2)
    print(f"T {len(T)} / C {len(C)}; median fullmove "
          f"{T.fullmove.median():.0f}/{C.fullmove.median():.0f}, median npm "
          f"{T.npm_light.median():.0f}/{C.npm_light.median():.0f}")
    return T, C


def extract(T, C):
    """FEN before the move and the played SAN, from the analyzed PGNs."""
    want = {}
    for df in (T, C):
        for gid, ply in zip(df.gid, df.ply):
            want.setdefault(gid, set()).add(int(ply))
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, "chess/data/*_analyzed.pgn.gz"))):
        with gzip.open(path, "rt") as fh:
            while True:
                game = chess.pgn.read_game(fh)
                if game is None:
                    break
                gid = game.headers.get("GameId", "")
                if gid not in want:
                    continue
                need = want[gid]
                board = game.board()
                ply = 0
                for mv in game.mainline_moves():
                    ply += 1
                    if ply in need:
                        out[f"{gid}|{ply}"] = {"fen": board.fen(),
                                               "san": board.san(mv)}
                    board.push(mv)
    n_want = sum(len(v) for v in want.values())
    if len(out) != n_want:
        sys.exit(f"ERROR: extracted {len(out)} of {n_want} positions")
    print(f"extracted {len(out)} positions from PGNs")
    return out


def analyse(T, C, fens, depth, subsample=None):
    if not os.path.exists(SF):
        sys.exit(f"ERROR: stockfish not at {SF} — see README")
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    eng.configure({"Threads": 1, "Hash": 128})
    rows = []
    for grp, df in (("T", T), ("C", C)):
        if subsample is not None:
            df = df.sample(subsample, random_state=7)
        for gid, ply in zip(df.gid, df.ply):
            e = fens[f"{gid}|{int(ply)}"]
            b = chess.Board(e["fen"])
            played = b.parse_san(e["san"])
            best = eng.analyse(b, chess.engine.Limit(depth=depth))["pv"][0]
            rec = dict(grp=grp, gid=gid, ply=int(ply),
                       best_forcing=forcing(b, best),
                       played_forcing=forcing(b, played),
                       best_is_played=(best == played),
                       reply_forcing=None)
            b.push(played)
            if not b.is_game_over():
                rep = eng.analyse(b, chess.engine.Limit(depth=depth))["pv"][0]
                rec["reply_forcing"] = forcing(b, rep)
            rows.append(rec)
    eng.quit()
    return pd.DataFrame(rows)


def perm_test(res, col, rng):
    a = res[res.grp == "T"][col].dropna().astype(float).values
    b = res[res.grp == "C"][col].dropna().astype(float).values
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    na = len(a)
    cnt = 0
    for _ in range(N_PERM):
        p = rng.permutation(pool)
        if abs(p[:na].mean() - p[na:].mean()) >= abs(obs):
            cnt += 1
    return obs, cnt / N_PERM


def main():
    T, C = build_sets()
    fens = extract(T, C)
    res = analyse(T, C, fens, DEPTH)
    res.to_csv(os.path.join(FEAT, "forcingtest.csv"), index=False)

    print(f"\n--- depth {DEPTH} ---")
    for g in ("T", "C"):
        d = res[res.grp == g]
        print(f"  {g} (n={len(d)}): best move forcing "
              f"{d.best_forcing.mean() * 100:.0f}% | played move forcing "
              f"{d.played_forcing.mean() * 100:.0f}% | best reply forcing "
              f"{d.reply_forcing.dropna().mean() * 100:.0f}% | played the best "
              f"move {d.best_is_played.mean() * 100:.0f}%")

    rng = np.random.default_rng(0)
    print(f"\n--- permutation on group label, {N_PERM:,} draws ---")
    for col, label in (("best_forcing", "H1 best move forcing"),
                       ("reply_forcing", "H2 best reply forcing"),
                       ("played_forcing", "   played move forcing")):
        obs, p = perm_test(res, col, rng)
        print(f"  {label}: T-C = {obs * 100:+5.1f} pp, p = {p:.4f}")

    c = res[res.grp == "C"]
    print("\n--- controls: does he find his own forcing moves? ---")
    print(f"  played the engine-best move when best was forcing: "
          f"{c[c.best_forcing].best_is_played.mean() * 100:.0f}% "
          f"(n={int(c.best_forcing.sum())})")
    print(f"  played the engine-best move when best was quiet:   "
          f"{c[~c.best_forcing].best_is_played.mean() * 100:.0f}% "
          f"(n={int((~c.best_forcing).sum())})")

    if D16:
        print("\n--- depth 16 replication, 60/60 subsample ---")
        r16 = analyse(T, C, fens, 16, subsample=60)
        for g in ("T", "C"):
            d = r16[r16.grp == g]
            print(f"  {g} (n={len(d)}): best forcing "
                  f"{d.best_forcing.mean() * 100:.0f}% | reply forcing "
                  f"{d.reply_forcing.dropna().mean() * 100:.0f}%")

    print(f"\nwrote {os.path.join(FEAT, 'forcingtest.csv')}")


if __name__ == "__main__":
    main()
