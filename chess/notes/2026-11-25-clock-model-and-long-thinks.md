# Clock model and long thinks (2026-11-25)

Exploratory and not pre-registered. Requested by Justin after the group F
null. Nothing here is a test result. Treat it as a lens and a set of leads.

## 1. Clock model, 3+2

`python3 chess/scripts/clockmodel.py /home/claude/features7`

Fitted on 3,526 games from the six settled blocks (76,839 own-move snapshots,
move 15+), and validated on the 645 3+2 games of the F block (held out).
Held-out Brier: eval only 0.1680, eval + clocks **0.1622**.

Full output:

```
eval-only held-out Brier on F block = 0.1680
clock held-out Brier on F block = 0.1622
==============================================================================
                 coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------
const          0.1394      0.210      0.663      0.508      -0.273       0.552
L              0.3184      0.104      3.060      0.002       0.114       0.522
a              0.5931      0.057     10.342      0.000       0.481       0.706
b             -0.6686      0.060    -11.141      0.000      -0.786      -0.551
La             0.0259      0.028      0.919      0.358      -0.029       0.081
Lb             0.0934      0.030      3.136      0.002       0.035       0.152
==============================================================================
games 3526 train / 645 test; snapshots 76839 14297

expected score (3+2, move 15+)   rows: engine win% | cols: my clock (opp 60s / opp 150s)
eval       5s    10s    20s    45s    90s   150s
 50%      22%    26%    32%    42%    51%    58%   | opp 150s: 13 16 21 29 37 44
 65%      31%    36%    44%    54%    64%    70%   | opp 150s: 21 25 31 41 51 58
 80%      44%    51%    59%    69%    77%    82%   | opp 150s: 33 39 47 58 67 74
 90%      60%    66%    73%    81%    87%    90%   | opp 150s: 50 57 64 74 81 86

cost of a 30s think (clock X -> X-28), opp 60s, in points of expected score:
50%: 40s:+12.8  60s:+8.1  90s:+5.2  150s:+2.9
65%: 40s:+14.6  60s:+8.5  90s:+5.0  150s:+2.6
80%: 40s:+14.6  60s:+7.6  90s:+4.1  150s:+1.9

example 80% eval, me 10s vs opp 150s: 39%;  same eval, clocks level 60/60: 72%
sanity, level eval & equal clocks: 20/20 47%  60/60 46%  150/150 44%
engine 75-85% bucket actual score (weighted) 66.3%

break-even: engine win% the move must reach after a 30s think (opp 60s)
60s: 50%->60%  90s: 50%->56%  150s: 50%->54%
60s: 65%->74%  90s: 65%->71%  150s: 65%->68%
60s: 80%->86%  90s: 80%->84%  150s: 80%->82%
```

Notes:
- **Engine "50%" is not 50% for Justin.** At level clocks it scores about 46%,
  and engine 75–85% positions actually score 66%. That is the known
  conversion weakness, now visible as a calibration gap.
- **Predictive, not causal.** A low clock at a given eval also marks a game
  that has been hard, so the clock coefficients likely overstate what a
  second is worth. The clean result in the README (opponent opening pace
  worth +8 pp) points the same way, which supports the direction, not the
  size.

## 2. What long thinks are spent on

Scripts in `chess/scripts/longthink/` (see the README there for the method).
3+2, 2026 + F blocks. Long = ≥ 15s (top 7% of moves, 30% of total think
time). Compared against 1,500 random quick moves (≤ 5s, move 8+).

| position type | long thinks | share | found a good move | quick moves share |
|---|---|---|---|---|
| only move (puzzle) | 261 | 7.3% | 47% | 13.9% |
| 2–3 good moves | 1,100 | 30.8% | 45% | 21.0% |
| 4+ fine moves | 1,543 | 43.2% | 67% | 28.4% |
| winning, several moves keep it | 331 | 9.3% | 82% | 16.7% |
| already lost (best < 20%) | 339 | 9.5% | 81% | 19.9% |

- **Long thinks at moves ≤ 15 in 4+ fine move positions: 729, or 20.4% of all
  long thinks**, mean 22s spent, with 141s left on average.
- Very long thinks (≥ 30s, n = 462) have almost the same mix (4+ fine 43%,
  2–3 good 31%, only move 8%, already lost 12%). Distraction cannot be
  separated from deliberate thought in this data.
- **The "found a good move" column does not mean thinking hurts.** Within
  each type, the positions that triggered a long think are harder than the
  ones played fast (for example, quick "only move" positions are mostly
  obvious recaptures). That is selection, not cost.

## 3. The clock lens on games (F block)

`lens.py` splits each own move's change in model expected score into a
clock part (board held fixed, clock before vs after) and a board part.

- Per game, move 15+: **about 11 points of expected score lost to clock, 75 to
  the board.**
- Long thinks: on average 2.6 points to clock and 5.7 to the board. Quick
  moves (≤ 5s): 0.06 and 2.6.
- By type, for F-block long thinks (clock / board, points): only move
  3.2 / 11.9; 2–3 good 2.8 / 7.7; 4+ fine 2.8 / 4.3; winning 2.1 / 4.5;
  already lost 1.6 / 2.4.

The costliest thinks that ended on a fine move anyway (4+ fine moves, and
the move played was within 5 points of best):

- https://lichess.org/z5IPokmY#97  move 49 Kf4: spent 21s with 24s left vs 41s, engine 51% -> clock cost 13.9 pts, board cost +0.2
- https://lichess.org/wol9SfoO#53  move 27 Bg4: spent 38s with 51s left vs 97s, engine 56% -> clock cost 13.7 pts, board cost +11.1
- https://lichess.org/Py4YvdAC#37  move 19 Qb8+: spent 25s with 36s left vs 101s, engine 64% -> clock cost 11.6 pts, board cost +4.7
- https://lichess.org/o0N6iLDZ#41  move 21 Rd2: spent 26s with 41s left vs 16s, engine 52% -> clock cost 10.8 pts, board cost +3.7
