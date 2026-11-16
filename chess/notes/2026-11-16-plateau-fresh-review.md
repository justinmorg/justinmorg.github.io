# Plateau period: a fresh review of where the wins are

Written 2026-11-16 at Justin's request: look at the games again without
starting from the README's conclusions, then say where the two agree.

**Status: exploratory, not pre-specified, scratch scripts not committed.**
Nothing here is a tested finding. Every comparison is Justin against his
opponents in the same games, which is a same-rating benchmark by construction.
The definitions below are enough to rebuild every number.

## Scope and definitions

- Games: 2,326 rated 3+2 / 5+0 Lichess games, 2025-07-01 to 2026-08-31.
  Q3 2025 (363), Q4 2025 (232), the 2026 corpus at the default filter (1,511),
  and the 220-game `pending/` batch. **The pending batch is included here and
  is not in any README figure.** No games after 2026-08-31 are in the repo, so
  nothing here bears on the group F block.
- Win chance: the Lichess curve, 1 / (1 + exp(-0.00368 x centipawns)), from the
  depth-12 evals. "+3" is a 75% win chance, "+1.1" is 60%.
- Big error: one move that drops the mover's win chance by 15 points or more.
- Lead: win chance at or above 75% on two consecutive plies, after move 8.
  Two plies so that a single bad eval cannot create one.
- Slip: the first ply, after a lead, at which the leader's win chance is below
  60%.
- Endgame: move 13+, and total non-pawn material 26 or less, or queens off and
  32 or less. This is not the README's phase definition.
- Free material: after the move, the other side has a capture worth 200cp or
  more by `hanging.see`.
- Intervals are 95% game-level bootstraps.

## Result 1: the largest gap is holding a lead

| | Justin | opponents |
|---|---|---|
| games with a lead | 57.2% | 55.0% |
| score from a lead | 75.3% | 81.3% |
| up a piece (3+ points, two own turns running): score | 74.7% | 82.8% |
| games reaching +1.1 | 71.4% | 64.0% |
| score from +1.1 | 64.3% | 72.4% |

Gap from a lead: -6.0 points [-9.4, -2.6]. Piece up: -8.2 [-12.7, -3.8]. The
piece-up row uses no engine. Present in every block (2026 75.3 vs 81.6; Q3
74.2 vs 79.6; Q4 76.5 vs 84.1; pending 76.8 vs 79.2) and both formats.
Closing it fully is 0.572 x 6.0 = about 3.4 game points per 100 games.

He gets ahead more often and gives it back more often; the two cancel to the
50% that matchmaking enforces.

## Result 2: it is not more errors while winning

- Big errors per game in which the side was ever at +3: 0.80 vs 0.79.
- Per move at +3 or better (move 13+): 6.2% vs 7.0% big errors; the gap is
  -0.83 points [-1.62, -0.10] in his favour, unchanged by clock matching.
- A lead slips in 39.8% of his leads (529 of 1,330) and 34.4% of theirs
  (440 of 1,280).

The slip itself looks the same on both sides:

| at the slip | Justin | opponents |
|---|---|---|
| median move | 25 | 26 |
| moves since the lead was first reached (median) | 6 | 5 |
| middlegame / endgame | 54% / 43% | 54% / 45% |
| win chance before, after | 77% to 42% | 79% to 43% |
| slip move leaves free material | 30% | 30% |
| median seconds on the slip move | 6 | 5 |

What differs is the result afterwards:

| after the slip | Justin | opponents |
|---|---|---|
| win / draw / loss | 37.6 / 7.8 / 54.6 | 48.9 / 8.9 / 42.3 |
| score | 41.5% | 53.3% |
| losses that are on time | 15% | 21% |

The engine curve is the wrong yardstick here (a 42% position, but see Result
4: at this level the player who slipped scores about 47.5%). Against that
norm both numbers are off by about six points, in opposite directions.

Per-move play after the slip, big-error rate: after his slips, him 8.9% and
them 9.0%. After their slips, them 8.2% and him 9.4%.

## Result 3: the clock lines up with it

Clock difference at the slip (leader's clock minus the other side's):

| leader is | Justin: share | score | opponents: share | score |
|---|---|---|---|---|
| 30s+ behind | 40% (214) | 33.4% | 17% (75) | 34.0% |
| within 30s | 48% (256) | 42.4% | 51% (223) | 50.2% |
| 30s+ ahead | 11% (59) | 66.9% | 32% (142) | 68.3% |

In the two outer rows the two sides score the same. The mix differs. His
opponents' row scores applied to his mix give 45.7%, so the mix covers about
7.6 of the 11.8 points. The remainder is in the "within 30s" row (42.4 vs
50.2, each roughly +/- 6) and is not established.

Median clocks at the slip: 3+2, his 67s against their 95s when he is the
leader, their 90s against his 73s when they are. 5+0: 151 vs 174, and
164 vs 153.

How the deficit builds:

- Time per move, 3+2: opening 5.4s vs 4.7s, middlegame 8.0s vs 7.1s, endgame
  3.9s vs 3.8s. Seconds used by move 25 (median): 142 vs 119.
- Median clock at move 30 in 3+2: 50s vs 75s. At move 40: 28s vs 53s.
- Thinks of 10s or more per game: 5.3 vs 4.3 (88s vs 73s per game).
- When he first reaches a lead he is a median 7s behind. By the slip he is
  19s behind. While holding the lead he spends 7.0s a move against their 5.7s.
  Opponents holding a lead: 14s ahead at the start, 11s ahead at the slip,
  6.1s a move against his 6.1s.
- Moves played at +3 or better with under 15s on the clock: 1,760 vs 1,085.

The extra time does not show up as accuracy after the opening. Middlegame
big-error rate 9.9% vs 9.4%; clock-matched gap +0.29 [-0.14, +0.68].

The same pattern at endgame entry from a level position (n = 312, score
44.1% [38.9, 49.5]): 20s+ behind 35.0% (113), within 20s 45.8% (144), 20s+
ahead 58.2% (55).

Applied at the first moment of the lead rather than the slip, the clock mix
covers about half the conversion gap (opponents' rates at his mix: 78.1%,
against his 75.3% and their 81.3%).

## Result 4: the panel says it is both halves, about equally

Added the same day, after Justin asked whether the problem is doing worse
after his own slip or failing to cash in on theirs. His own games cannot
separate these, because his opponents are the only benchmark in them. The
thread 9 panel can: 88 players (all annotated player-months in
`data/panel/ann/`, improvers and controls, both Septembers), 39,564 games,
17,053 slips counting both sides of each game. Same definitions as above.
Two-thirds of panel games are 5+0, so norms are matched to his format mix.

Norm: the player who slips scores 47.5% (3+2 48.0%, 5+0 46.9%) from a
position the engine curve calls 42%.

| | Justin | panel norm, same format | difference |
|---|---|---|---|
| score after his own slip | 41.5% | 47.5% | -6.0 [-10.0, -2.2] |
| score after the opponent's slip | 46.7% | 52.5% | -5.8 [-10.4, -1.3] |

Per player, he is at the 22nd percentile of the 88 on the first and the 23rd
on the second (panel medians 46.8% and 53.9%). Restricting to the 60 players
rated 1250-1550 gives the 22nd on both.

Clock, same comparison:

- Share of own slips at 30s+ behind: his 40%, panel median 22%
  (IQR 15-38%); he is at the 76th percentile.
- Median clock difference at own slip: his -19s, panel median -1s.
- When the opponent slips, the panel player is typically 7s ahead of them; he
  is 11s behind.
- Panel slipper score by clock state (3+2 / 5+0): 30s+ behind 36.9% / 32.8%,
  within 30s 49.7% / 48.6%, 30s+ ahead 58.5% / 62.6%.

Matching the norm on clock state as well as format: own slip -3.4
[-7.3, +0.3], opponent's slip -2.9 [-7.4, +1.3]. So clock state covers a bit
under half of each, and what is left is not distinguishable from zero.

Lead conversion against the panel: his 75.3% is at the 23rd percentile (panel
77.6%); opponents convert 81.3% against him where the panel concedes 76.6%.
He gives up about two points converting his own leads and about four letting
opponents convert theirs.

Caveats: improvers were selected for gaining rating, which could lift the
norm slightly (controls alone: 49.8% / 48.7% as slipper). Panel opponents are
anonymous and unmatched. Result 3's "mix covers 7.6 of 11.8 points" used his
opponents as the norm and is superseded by the panel figures here.

## Other results

- Opening (moves 1-12): big errors 3.8% vs 4.4%, gap -0.55 [-0.78, -0.30].
- Endgames between -3 and +3: big errors 10.5% vs 8.8%, gap +1.64
  [+0.73, +2.49]; clock-matched +1.77 [+0.64, +2.70]. Endgames at +3 or
  better: 4.6% vs 5.5%, in his favour.
- Free material: 25% of his big errors after move 8 leave it, 24% of theirs.
  In winning middlegames 31% vs 29%. Given a free capture he takes one 90.4%
  of the time, they do 89.0%.
- Time forfeits: 188 wins, 112 losses. 29% of his flag losses were from a
  board at +3 or better (about 1.4 games per 100).

## Against the README

Agree:

- Openings are a strength.
- Close endgames are a skill gap, and it is not his own clock.
- The level-endgame score (44.1% here, 42.7% there).
- Flags and resignations are not leaks.
- The hanging-material rate is flat and at peer level; "MG winning: better
  than peers" in the payoff table.
- Converting winning positions is the main weakness ("What this is for").

Differ:

1. Hanging material in winning middlegames as the top priority (group P / F).
   It is a quarter to a third of big errors, at the same rate as opponents.
   The README had already moved off this by 2026-10-24.
2. "EG ahead" as the top payoff row. Here the deficit is in endgames between
   level and +3. Endgames at +3 or better are at or above peer level. The
   bucket and phase definitions differ, so this is a refinement, not a
   contradiction.
3. The clock. The README records the chronic deficit and concludes "nothing
   here licenses moving faster", because clock state is downstream of
   position difficulty. That objection stands. What is added here is the
   opponent comparison: in the same clock state, opponents get the same
   results, and the extra time buys no measured accuracy after move 12. This
   moves the clock from parked to the leading candidate. It does not make it
   causal.

## What this could not see

- Whether spending less time would cost accuracy. No game here has him playing
  faster on purpose. The opening edge may be partly bought with the extra 0.7s
  a move.
- Depth 12 is weakest in endgames. Both players are judged by the same engine,
  so the comparison is fair, but the win-chance figures there are soft.
- Roughly 0.3% of evals are corrupt (README, "Individual evals can also just
  be wrong"). The two-ply lead rule and the material-only row guard against it.
- The "within 30s" residual and all sub-splits by block are too small to read.

## What it changes

The post-block plan stands. One addition for blitz, as a habit and not a
test: be level with the opponent's clock around move 20, and do not slow down
once ahead.
