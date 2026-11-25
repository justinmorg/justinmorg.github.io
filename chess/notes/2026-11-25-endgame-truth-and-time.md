# Endgame truth check, time map and practice decks (2026-11-25)

Exploratory, not pre-registered. Justin asked for three things together: check
his endgame errors against exact or deeper truth, map where his endgame clock
goes against how many moves were actually fine, and build practice decks from
his own recurring positions. Two prior leads this tests: the plateau review's
close-endgame gap (big errors 10.5% vs 8.8%, notes/2026-11-16, "Other
results" and "Addendum") and the level-endgame 42.7% (README).

Scripts: `chess/scripts/egtruth/` — `extract.py` → `tb.py` → `engine.py` →
`analyze.py` (`verify.py` for the depth-20 sample). Decks:
`chess/scripts/build_study_egtruth.py`. Data committed:
`data/egtruth_tb.jsonl.gz` (17,797 tablebase answers),
`data/egtruth_eng_close.jsonl.gz` (38,466 MultiPV-4 searches),
`data/egtruth_verify_d20.jsonl.gz` (600 depth-20 checks). `analyze.py` reads
the plain `.jsonl` (gunzip first) and writes `tb_rows.csv.gz` /
`eng_rows.csv.gz` to `/home/claude/eg/` (path hard-coded), which the deck
builder takes as arguments.

## Scope and definitions

- Corpus: `studylib.load()`, Lichess 3+2 / 5+0. Plateau = 2024h2, 2025q1–q4,
  2026, pending; treat = 2026_fblock. 2023 and 2024rest excluded. Both sides'
  moves (opponents are the same-game benchmark, as in the plateau review).
- Endgame = `build_study_endgames.is_endgame` (move 13+, npm ≤ 26, or queens
  off and npm ≤ 32). 128,249 endgame plies (him 64,160, opp 64,089).
- TB part: ≤ 7 men, Lichess 7-man tablebase. Mover result before / after the
  move played; cursed-win and blessed-loss count as draws (50-move rule; Lichess
  enforces it). TB error = result got worse. `keep` = legal moves that keep it.
- Engine part: > 7 men and depth-12 mover win chance 0.25–0.75 ("close").
  Stockfish 17.1, 2 threads, 150k nodes, MultiPV 4 (median depth 13 — barely
  deeper than the corpus's 12; the multi-PV is the point, for the move count).
  gap = wp(best) − wp(played), Lichess curve. Error = gap ≥ 0.15. good = moves
  in the top 4 within 0.08 of best; "4+" = all four.
- Depth-20 check (`verify.py`): 200 errors + 100 non-errors per side, seed 11,
  depth 20 / 3 s cap. **90% of errors confirmed at ≥ 0.15 (him 91%, opp 90%);
  98% at ≥ 0.10; non-errors 3% him / 6% opp would have been errors.** The label
  is equally good for both sides, so the him-vs-opp gaps are fair.
- spent = own clock before − after + increment; negatives (clock glitches)
  dropped. Intervals: 2,000-draw game bootstrap on the him − opp difference.

## Headline (plain)

1. **Small endgames (≤ 7 men): no gap.** He lets tablebase wins go and loses
   tablebase draws at the same rate as his opponents.
2. **Bigger close endgames: the gap is real** and survives the deeper check:
   12.2% vs 10.3% (+1.9 [+1.3, +2.5]); same in the F block (+2.0 [+0.7, +3.3]).
3. **Nobody's time tracks difficulty.** Median 2–3 s per move whether one move
   or many are fine, for both players.
4. **Half his excess errors come where four or more moves were fine**, and at
   ≤ 20 s on his clock that rate doubles relative to opponents at the same
   clock (11.0% vs 5.4%).

## Full output

```
TB rows: 18209  games: 857  by era: {'plateau': 15159, 'treat': 3050}

## TB 1. Error rates where an error was possible

| cut | his / their moves | him | opp | gap [95%] |
|---|---|---|---|---|
| winning (tb): let the win go | 3844 / 3458 | 4.2 | 4.8 | -0.6 [-1.8, +0.6] |
| drawn, a losing move exists: lost the draw | 1505 / 1326 | 9.1 | 10.0 | -0.9 [-3.6, +1.7] |
| winning, plateau | 3086 / 3034 | 4.4 | 4.9 | -0.6 [-2.0, +0.9] |
| drawn, plateau | 1256 / 1118 | 9.6 | 10.2 | -0.6 [-3.5, +2.4] |
| winning, treat | 758 / 424 | 3.3 | 3.5 | -0.2 [-2.5, +1.9] |
| drawn, treat | 249 / 208 | 6.4 | 9.1 | -2.7 [-9.0, +3.1] |

## TB 2. Winning positions by type and by piece moved

| cut | his / their moves | him | opp | gap [95%] |
|---|---|---|---|---|
| minor-piece ending | 565 / 613 | 5.1 | 2.3 | +2.8 [+0.4, +5.5] |
| pawn ending | 720 / 1011 | 4.0 | 4.5 | -0.4 [-2.7, +2.1] |
| queen ending | 751 / 371 | 1.2 | 1.1 | +0.1 [-1.3, +1.4] |
| queens and pieces | 410 / 299 | 0.5 | 3.3 | -2.9 [-6.0, -0.2] |
| rook ending | 1091 / 877 | 5.9 | 8.4 | -2.6 [-5.4, +0.5] |
| rooks and minor pieces | 307 / 287 | 8.8 | 6.3 | +2.5 [-1.9, +7.5] |
| moved: K | 1104 / 1205 | 5.0 | 5.1 | -0.1 [-1.9, +1.9] |
| moved: N | 126 / 117 | 7.1 | 1.7 | +5.4 [-0.1, +12.5] |
| moved: P | 1151 / 1206 | 3.6 | 5.1 | -1.6 [-3.4, +0.2] |
| moved: Q | 679 / 388 | 1.2 | 1.5 | -0.4 [-1.8, +1.2] |
| moved: R | 684 / 462 | 6.0 | 7.1 | -1.1 [-4.6, +2.2] |

 drawn (defending) by type

| cut | his / their moves | him | opp | gap [95%] |
|---|---|---|---|---|
| minor-piece ending | 213 / 180 | 4.2 | 11.1 | -6.9 [-14.1, -0.2] |
| pawn ending | 307 / 234 | 11.1 | 11.1 | -0.0 [-6.5, +6.2] |
| queen ending | 105 / 99 | 9.5 | 4.0 | +5.5 [-1.4, +15.3] |
| rook ending | 605 / 559 | 10.2 | 9.8 | +0.4 [-3.7, +4.5] |
| rooks and minor pieces | 244 / 228 | 5.7 | 11.0 | -5.2 [-11.5, -0.2] |
| moved: K | 692 / 643 | 12.1 | 11.5 | +0.6 [-3.2, +4.6] |
| moved: P | 186 / 198 | 5.9 | 13.1 | -7.2 [-13.3, -1.6] |
| moved: R | 405 / 343 | 7.4 | 6.4 | +1.0 [-3.2, +5.4] |

## TB 3. Only moves vs many good moves (winning positions)


winning

| moves that keep it | his moves | his err | opp err | his median s | opp median s | his mean s | opp mean s |
|---|---|---|---|---|---|---|---|
| 1 (only move) | 272 | 24.6% | 25.1% | 1 | 1 | 1.9 | 2.0 |
| 2-3 | 257 | 14.4% | 9.8% | 1 | 1 | 2.1 | 1.8 |
| 4-6 | 342 | 7.0% | 4.1% | 1 | 1 | 1.9 | 2.1 |
| 7+ | 2973 | 1.1% | 1.4% | 1 | 2 | 1.9 | 2.1 |

drawn, defending

| moves that keep it | his moves | his err | opp err | his median s | opp median s | his mean s | opp mean s |
|---|---|---|---|---|---|---|---|
| 1 (only move) | 341 | 21.4% | 21.0% | 1 | 1 | 1.7 | 2.2 |
| 2-3 | 219 | 15.1% | 16.3% | 2 | 1 | 2.2 | 1.9 |
| 4-6 | 205 | 5.9% | 9.6% | 2 | 2 | 2.4 | 2.4 |
| 7+ | 740 | 2.6% | 3.4% | 2 | 2 | 2.7 | 3.0 |

## TB 4. Depth-12 label against the tablebase (his + opp moves, <= 7 men)

d12 flags: 671  of which TB errors: 557  (83%)
TB errors: 595  of which d12 flagged: 557  (94%)

## TB 5. Game level: first time a side reaches a TB win on its own move

| | games | converted (won) | drawn | lost |
|---|---|---|---|---|
| opp | 459 | 80.2% | 13.1% | 6.8% |
| him | 391 | 76.5% | 15.3% | 8.2% |
  plateau: him 323 games 76.5% won; opp 392 games 79.3% won
  treat: him 68 games 76.5% won; opp 67 games 85.1% won
first TB-drawn position with a losing move available: share NOT lost
  opp: 226 games, held (draw or win) 68.1%
  him: 247 games, held (draw or win) 67.6%


ENGINE rows (close, > 7 men): 38466  games: 2005  median depth: 13.0

## E1. Error rate, close endgames > 7 men

| cut | his / their moves | him | opp | gap [95%] |
|---|---|---|---|---|
| all (deep engine) | 19434 / 19032 | 12.2 | 10.3 | +1.9 [+1.3, +2.5] |
| all (depth-12 label) | 19434 / 19032 | 11.3 | 9.4 | +1.8 [+1.2, +2.5] |
| deep, plateau | 15984 / 15671 | 12.4 | 10.5 | +1.9 [+1.3, +2.6] |
| deep, treat | 3450 / 3361 | 11.4 | 9.5 | +2.0 [+0.7, +3.3] |
| minor-piece ending | 1262 / 1194 | 11.9 | 8.4 | +3.5 [+1.3, +5.6] |
| pawn ending | 401 / 407 | 17.0 | 15.5 | +1.5 [-2.9, +6.1] |
| queen ending | 443 / 423 | 14.0 | 9.0 | +5.0 [+1.3, +8.8] |
| queens and pieces | 1073 / 1068 | 13.1 | 12.2 | +1.0 [-1.9, +3.8] |
| rook ending | 4540 / 4408 | 10.9 | 8.4 | +2.6 [+1.4, +3.7] |
| rooks and minor pieces | 11715 / 11532 | 12.5 | 10.9 | +1.5 [+0.8, +2.3] |
| moved: B | 2196 / 1888 | 11.4 | 9.4 | +2.0 [-0.1, +3.9] |
| moved: K | 4124 / 4047 | 11.8 | 9.9 | +1.9 [+0.5, +3.4] |
| moved: N | 2244 / 1916 | 12.2 | 11.0 | +1.2 [-0.7, +3.2] |
| moved: P | 4502 / 4578 | 13.5 | 10.7 | +2.8 [+1.5, +4.1] |
| moved: Q | 496 / 631 | 13.5 | 11.9 | +1.6 [-2.3, +5.7] |
| moved: R | 5872 / 5972 | 11.8 | 10.2 | +1.6 [+0.4, +2.7] |
| mover has a passed pawn | 5630 / 6204 | 14.3 | 11.6 | +2.7 [+1.5, +3.9] |
| other side has a passed pawn | 6969 / 6036 | 14.7 | 12.7 | +2.0 [+0.8, +3.2] |

d12 flags 3977, deep agrees 3435 (86%); deep errors 4335, d12 flagged 3435 (79%)

## E2. Time map, close endgames > 7 men

| good moves | share of his moves | his err | opp err | his median s | opp median s | his mean s | opp mean s |
|---|---|---|---|---|---|---|---|
| 1 (only move) | 20% | 22.4% | 20.1% | 2 | 2 | 3.8 | 3.7 |
| 2-3 | 22% | 16.1% | 13.4% | 3 | 3 | 4.7 | 4.7 |
| 4+ (anything sensible) | 58% | 7.2% | 5.2% | 3 | 3 | 5.2 | 5.0 |

By clock band (own clock before the move), his moves vs theirs:
| clock | gb | his n | his err | opp err | his mean s | opp mean s |
|---|---|---|---|---|---|---|
| <=10s | 1 (only move) | 216 | 31.0% | 26.6% | 1.8 | 1.9 |
| <=10s | 2-3 | 220 | 21.8% | 15.0% | 2.1 | 2.1 |
| <=10s | 4+ (anything sensible) | 440 | 13.6% | 4.8% | 1.9 | 2.2 |
| 11-20s | 1 (only move) | 317 | 24.6% | 21.9% | 2.3 | 2.3 |
| 11-20s | 2-3 | 360 | 17.2% | 14.6% | 2.7 | 2.7 |
| 11-20s | 4+ (anything sensible) | 856 | 9.7% | 5.8% | 2.7 | 2.9 |
| 21-40s | 1 (only move) | 482 | 24.5% | 28.2% | 3.2 | 3.3 |
| 21-40s | 2-3 | 475 | 16.4% | 16.5% | 3.7 | 3.9 |
| 21-40s | 4+ (anything sensible) | 1096 | 8.5% | 5.8% | 4.2 | 4.3 |
| 41-90s | 1 (only move) | 1147 | 22.2% | 16.9% | 4.2 | 3.9 |
| 41-90s | 2-3 | 1240 | 15.9% | 12.7% | 4.9 | 5.2 |
| 41-90s | 4+ (anything sensible) | 3149 | 6.5% | 5.4% | 5.5 | 5.6 |
| >90s | 1 (only move) | 1749 | 20.6% | 19.3% | 4.1 | 3.9 |
| >90s | 2-3 | 2019 | 15.4% | 12.9% | 5.4 | 5.0 |
| >90s | 4+ (anything sensible) | 5668 | 6.4% | 5.0% | 5.9 | 5.3 |

Only-move positions: error rate by time spent (his / theirs)
  0-2s: him 2079 moves 16.8% | opp 2285 moves 12.4%
  3-5s: him 1061 moves 23.7% | opp 1099 moves 24.2%
  6-10s: him 531 moves 34.1% | opp 527 moves 34.5%
  11s+: him 240 moves 40.4% | opp 241 moves 42.7%
Many-good-move positions: share of moves by time spent, and seconds spent per game
  him: 0-2s 36%, 3-5s 32%, 6-10s 20%, 11s+ 12%
  opp: 0-2s 38%, 3-5s 32%, 6-10s 19%, 11s+ 11%
mean seconds per game (close >7-man endgame moves) by good-move class:
 gb    1 (only move)   2-3  4+ (anything sensible)
mine                                             
0               8.0  10.7                    27.9
1               7.7  10.4                    30.3

## E4. Where the excess is: good-move class x clock, time spent

| cut | his / their moves | him | opp | gap [95%] |
|---|---|---|---|---|
| 4+ good, clock <= 20s | 1296 / 1077 | 11.0 | 5.4 | +5.6 [+3.3, +8.0] |
| 4+ good, clock 21-90s | 4245 / 3204 | 7.0 | 5.5 | +1.6 [+0.3, +2.7] |
| 4+ good, clock > 90s | 5668 / 6255 | 6.4 | 5.0 | +1.4 [+0.6, +2.3] |
| only move, clock <= 20s | 533 / 482 | 27.2 | 23.9 | +3.3 [-2.1, +8.5] |
| only move, played in 0-2s | 2079 / 2285 | 16.8 | 12.4 | +4.4 [+2.4, +6.5] |
| 4+ good, played in 0-2s | 4090 / 3981 | 6.8 | 4.4 | +2.4 [+1.4, +3.5] |
| 4+ good, 3s or more | 7119 / 6555 | 7.4 | 5.6 | +1.8 [+1.0, +2.6] |
| 3+2 only | 15127 / 14775 | 12.3 | 10.3 | +2.0 [+1.4, +2.7] |
| 5+0 only | 4307 / 4257 | 12.0 | 10.4 | +1.6 [+0.4, +2.9] |

excess errors (his moves x (his rate - opp rate)) by class: {'1 (only move)': 92, '2-3': 117, '4+ (anything sensible)': 225} total 435

4+ good errors that leave a winning capture (scanlib.winning_captures after the move):
             mean  count
low   mine              
False 0     0.204    485
      1     0.194    660
True  0     0.224     58
      1     0.287    143
baseline, 4+ good non-errors (3,000 sampled): {0: 0.031, 1: 0.035}
piece moved in 4+ good errors at clock <= 20s:
piece     B     K     N     P     Q     R
mine                                     
0      0.07  0.12  0.10  0.17  0.17  0.36
1      0.07  0.19  0.09  0.24  0.05  0.36

## E3. Depth-20 verification sample

err n=400 confirmed gap>=0.15: 90% gap>=0.10: 98%
ok n=200 confirmed gap>=0.15: 4% gap>=0.10: 9%
   err opp n=200 confirmed 90%
   err him n=200 confirmed 91%
   ok opp n=100 confirmed 6%
   ok him n=100 confirmed 3%
```

Extra (`analyze.py` does not print this; one-off): of the first-TB-win games
he did not win (92 of 391), 14 ended on time and 78 on the board; opponents 15
and 76 of 459. Clock at his first TB win, median 36 s; opponents' 49 s. The
conversion difference, −3.7 pts, has interval [−9.2, +1.8].

## Reading it

- **TB part.** Every rate is at par or better: winning −0.6 [−1.8, +0.6],
  drawn −0.9 [−3.6, +1.7]. Sub-cuts wobble both ways (minor-piece endings +2.8
  [+0.4, +5.5] winning but −6.9 [−14.1, −0.2] drawn; ~20 cuts, read none of
  them). Errors concentrate where 1–3 moves keep the result (only move ~25% for
  both sides), and nobody spends more than ~2 s there.
- **Depth-12 vs truth in small endgames.** 83% of depth-12 flags are real
  tablebase errors and it catches 94% of them. In bigger close endgames 86% of
  depth-12 flags are confirmed by the deeper pass, and depth 12 catches 79% of
  the deeper pass's errors. Adequate for rates; every
  card is re-checked separately.
- **Engine part.** The gap is broad (every piece type points the same way),
  widest in rook endings +2.6 [+1.4, +3.7], minor-piece endings +3.5 [+1.3,
  +5.6], queen endings +5.0 [+1.3, +8.8], pawn moves +2.8 [+1.5, +4.1], with a
  passed pawn on the board (either side's). Agrees with the plateau addendum.
  3+2 and 5+0 agree.
- **Time map.** Only-move positions are 20% of his close-endgame moves, 4+ are
  58%; time spent hardly differs (means 3.8 / 4.7 / 5.2 s; opponents 3.7 / 4.7 /
  5.0). Longer thinks go with *more* errors on only-moves for both sides
  (0–2 s 17% → 11 s+ 40%) — difficulty confound, not evidence that thinking
  hurts. He spends ~2 s more per game than opponents in 4+ positions; not a
  meaningful clock drain.
- **Where the excess is.** 435 excess errors total: only-move 92, 2–3 good 117,
  4+ good 225. In 4+ positions at ≤ 20 s, 11.0% vs 5.4% (+5.6 [+3.3, +8.0]);
  21–90 s +1.6, > 90 s +1.4. Played in 0–2 s: 4+ good +2.4 [+1.4, +3.5],
  only-move +4.4 [+2.4, +6.5]. At low clock his 4+ errors are more king and
  pawn moves (K 19% / P 24% vs 12% / 17%), and about a quarter of them leave a
  winning capture (29% vs a 3.5% baseline for fine moves); most do not.
- **Clock caveat.** He reaches ≤ 20 s more often than opponents (known
  chronic deficit), so the low-clock cell is clock-matched but not
  position-matched: positions he reaches short of time may be harder in ways
  "4+ good" does not capture. "4+" comes from a depth-13 MultiPV-4 search and
  is approximate.

## What it changes

- Endgame study: priority is close endgames with pieces still on (rook
  endings, passed pawns), not K+P / basic tablebase technique. The existing
  eg_kpk / eg_square decks stay but drop in priority.
- A concrete habit: in endgames, sort each move as one-move-or-many; if
  nothing forcing is happening and the clock is short, play a safe move —
  before king and pawn moves check what the move stops guarding.
- Feeds the parked "trades from level positions" idea: no evidence here that
  trading down into small endgames costs him anything at the board.

## Decks built (chess-study, Endgames group)

- `eg_tm` — six lesson cards summarizing the above.
- `eg_om` "One move or many?" — 30 of his close > 7-man positions: 15
  only-move positions he missed (deep error, good = 1, gap ≥ 0.2) and 15 where
  ≥ 4 moves were fine and he spent ≥ 10 s. Each re-checked at SF17.1 depth 18,
  MultiPV 5: only-move cards need best − second ≥ 0.15 and best wp 0.2–0.85;
  many-move cards need ≥ 4 moves within 0.06 and his move within 0.08. Step 1
  asks one-or-many, step 2 the move. F-block games first, one card per game.
- `eg_tb` "Win it or hold it" — 30 of his ≤ 7-man TB errors (16 win, 14 draw)
  where 1–3 moves kept the result; accepts every keeping move; shows the
  tablebase line. F-block games first, one per game.
- Own caches (`study/tb_cache_egtruth.json`, `study/engine_cache_egtruth.json`)
  so `build_study_endgames.py`'s pruning of the shared tablebase cache cannot
  break these decks; offline rebuild verified byte-identical.
