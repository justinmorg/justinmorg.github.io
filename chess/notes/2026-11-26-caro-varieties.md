# Caro-Kann by variety (2026-11-26, exploratory, not pre-registered)

Parked idea 1 of 2026-11-25. Study build, not a test. Every figure below was
looked at before any framing was chosen; treat all of it as descriptive.

Data: `studylib.load()` (Lichess, all depth-12 blocks + pending, 3+2/5+0,
6,479 games), Black after 1.e4 c6: **1,871 games**. Benchmark: thread-9 panel
players' own games as Black after 1.e4 c6 (`data/panel/ann/`, SF16 depth 12,
15 players, 681 games). P1 = own move with win-prob drop >= 15 (README
convention). Scripts in `chess/scripts/caro/`:

| script | output |
|---|---|
| `classify.py` | variety (move order) + structure at ply 20 |
| `analyze.py` | score, P1/100 moves 4-12 and 13-30 vs panel, mean wp after moves 10/15/20/25; `/tmp/caro_errors.csv` |
| `movetypes.py` | per-SAN P1 rate vs his variety baseline; `/tmp/caro_moves.pkl` (needed by the next three) |
| `breaks.py` | flagged moves, him vs panel |
| `setups.py` | by White set-up within variety |
| `kside.py` | kingside pawn moves vs panel, bootstrap; opponent-rating check c3 vs Nc3 |
| `kingzone.py` | White's depth-12 best reply after each P1: check / lands within 2 files & 3 ranks of Black's king |
| `select_moments.py` | caro_moves deck positions -> `chess/study/caro_moments.json` |

## Varieties

| variety | games | score | P1/100 mv 4-12 (panel) | P1/100 mv 13-30 [95%] (panel) | wp after 10/15/20/25 |
|---|---|---|---|---|---|
| Advance | 532 | 49% | 4.0 (4.1) | 8.4 [7.7, 9.1] (9.8) | 52/53/53/50 |
| Exchange (d4) | 483 | 51% | 3.3 (3.4) | 8.5 [7.8, 9.2] (10.4) | 51/51/47/45 |
| Exchange, no d4 (2.Nf3/2.Nc3 exd5) | 99 | 53% | 3.5 (4.2) | 9.0 (10.5) | 52/52/50/51 |
| Panov | 50 | 44% | **8.4** (4.0) | 9.1 (10.7) | 43/48/48/50 |
| 4.Nxe4 Nf6 | 141 | 46% | **5.5** (n/a, panel plays 4...Bf5: 5.2) | 9.3 (4...Bf5: 8.4) | **44/42/41/39** |
| 2.Bc4 | 187 | 48% | 3.1 (4.7) | 8.1 (9.1) | 59/59/60/58 |
| Two Knights / Fantasy / 2.d3 / other | 67 / 30 / 34 / 248 | 48-50% | | | |

He never plays 4...Bf5; 4...Nf6 in all 141 4.Nxe4 games; 5.Nxf6+ exf6 in all
77 where White took. Engine depth 20 after 4.Nxe4: Nf6 +0.29, Bf5 +0.36 —
the line is not the problem. Panel n for single varieties is small (1-183).

**Error rate is at or below the panel in every main variety.** The Caro
weakness is not a mistake-rate gap.

## By White set-up (setups.py; /tmp/c3.py scratch, not committed)

- Exchange, White **c3** (no c4) 137 games 45%, wp 45 -> 37 (moves 12 -> 25);
  White **Nc3** 379 games 52%, 54 -> 49. Opponent minus him +1 Elo in both.
  His mean per-move wp loss is the same (0.041 vs 0.043, own moves 6-30), so
  the drift is White playing the c3 set-up better, not him playing worse.
  White Ne5 41% vs 21%, Bd3 43% vs 21%, Qc2 26% vs 2%; his ...b5/...b4 in
  69/137 (50%) vs 26%; ...Bxf3 in 80/137.
- Advance: 4.c3 156 games 44% (wp12 54, i.e. conversion); 4.Nf3 90 56%;
  **4.dxc5 30 games 42%, wp12 38**; 2.Nf3 lines 159 49%. With g4/h4 by White:
  27 games ~70%. His reply to 4.dxc5 is ...Nc6 in ~all; depth 20: 4...e6 +0.30,
  4...Nc6 +0.58. Two of the twelve sampled ...d4 errors were in 4.dxc5 lines
  ending Qxc6 mate/+ (queen on f3 behind the d5 pawn after Bxc6+ bxc6).
- 4.Nxe4 Nf6: 5.Nxf6+ 77 games 46% (wp12 44); 5.Ng5 38 games 39%.
- Light bishop for knight by move 12: Advance 296 games 49% vs kept 236 49%;
  Exchange 344 54% vs 238 47%. **Not a bad trade**; lessons say so.

## Theme moves (own moves 6-30)

| variety | move | his P1% (n) | panel P1% (n) |
|---|---|---|---|
| Advance | ...d4 | 26 (114) | 23 (13) |
| Advance | ...f6 | 22 (107) | 12.5 (40) |
| Advance | ...g5 | 26 (39) | 6 (16) |
| Exchange | ...e5 | 27 (93) | 25 (20) |
| Exchange | ...f6 | 22 (63) | 0 (16) |
| Exchange | ...Nf5 | 23 (48) | 6 (53) |
| Exchange | ...Ne4 | 16 (205) | 15 (52) |
| 4.Nxe4 Nf6 | ...g5 | 33 (30) | — |

Moves picked by looking at his own rates first (post hoc), so his column is
biased upward; the panel column is the check.

Kingside pawn moves (f/g/h-pawn, non-capture), kside.py, game bootstrap:
him 12.3% P1 vs 7.1% other moves (diff [+3.4, +6.8]), 4.7% of moves; panel
11.9% vs 8.0% ([+1.2, +6.7]), 4.7% of moves. **Same for peers, same
frequency** — an opening property, not his gap. kingzone.py: 40% of his P1s
(Advance 41, Exchange 40, 4.Nxe4 40) answered by a check or a king-zone move;
panel 36-39% (4...Bf5 58% on n=24). Also not his gap.

## Decks (chess-study group "Caro-Kann by variety")

Built by `scripts/build_study_caro.py`; caches `study/engine_cache_caro.json`
(SF 17.1), `study/caro_moments.json`. Offline rebuild byte-identical
(verified with `STOCKFISH_PATH=/nonexistent`).

- `caro_lessons` (CK, 5): which Caro (move-three question), what the data
  says (this note in plain words), Advance (walls: d5 blocks Qf3->c6, f7
  guards e6/g6; 4.dxc5 e6), Exchange vs c3 (queenside vs kingside race, h7
  guard, ...e5), 4...Nf6 (queenside majority -> keep queens, ...Nd7-f8).
  Each `Q` engine-checked at depth 20 (tol 70cp); two examples are his games
  (sTcnZYBb ...d4?? Qxc6#, BXGZNwxV ...f6? Qxe6+, 5EyAx6YO ...Bxg5?? Qxh7#,
  LE3Rl50r ...e5? Nxd5).
- `caro_which` (CW, 24): 6 each Advance / Exchange (carlsbad struct) / Panov
  (c4 played) / 4.Nxe4 Nf6 5.Nxf6+ exf6, Black to move at ply 12-18; keys
  from move order. Two choices: variety, then plan.
- `caro_moves` (CB, 36): his theme moves (kside pawn / Advance ...d4 /
  Exchange ...e5), contested (depth-12 wp 30-80%), one per game, not on the
  drill pages. Depth 18: bad = played >= 12 points below best (22), fine =
  within 3 (14). Accept = top-5 within 5 points. Mix: Advance 8/6, Exchange
  8/6, 4...Nf6 5/3. Explanation text computed (`why_bad`): f7->e6/g6 square,
  d5 on the reply's line, e5 opening d5, king-cover reply, else material at
  the last quiet ply of an 8-ply line (stated only for 1-5 points).
  No eval stated before the answer.

Not done: 4...Bf5 as an alternative (Justin does not want to change
openings); Two Knights / Fantasy (n 67 / 30); the Panov beyond the existing
OL-caro-plans card.
