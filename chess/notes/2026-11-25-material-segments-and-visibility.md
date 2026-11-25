# Errors by what you can see on the board, and how visible they are (2026-11-25)

Exploratory, not pre-registered. Asked for by Justin: re-segment losing moves by
things identifiable at the board (material, clocks, queens, phase) instead of
engine eval, with a clock-aware error definition; and place errors on a
spectrum from "obvious next move" to "engine-only".

Scope: Lichess 3+2, blocks 2024H2, Q1–Q4 2025, 2026, TREAT; own moves,
fullmove >= 6. 4,605 games (2,225 lost), 154,440 own-move rows.
Scripts: `chess/scripts/visibility/` (sandbox paths hard-coded at the top of
each; run build.py → seg.py → playout.py → paired.py; opp.py; deep.py).
Engine outputs committed: `data/vis_playouts.jsonl.gz`, `data/vis_deep16.jsonl.gz`.

## Definitions

- **Clock-aware cost.** `clockmodel.py` spec refitted on move 8+ (train six
  settled blocks, held-out TREAT Brier 0.1834 vs eval-only 0.1879). Cost of a
  move = E(wp_before, clocks after) − E(wp_after, clocks after): the board part
  of the change in expected score, clocks held fixed. Error = cost >= 0.10
  (10 points of expected score). 13,092 errors.
  Effect of the clock terms: the same engine drop counts ~15–20% less with
  either clock under 10s than with 90s+. 3,058 plain wp_error>=0.10 moves fall
  below the line, mostly because the model also encodes the real conversion
  rate (engine 80% scores ~66%), which shrinks mid-size drops. Segment ranking
  is the same either way.
- **Perceived material.** `mat_bal` (1/3/3/5/9) plus the best SEE recapture on
  the square the opponent just captured on, so a half-finished trade reads as
  level.
- Depth check: 300 random errors re-evaluated at depth 16 — 82% still >= 10
  points, 96% >= 5.

## Part 1 — lost games, share of error cost by observable state

| material (perceived) | share of moves | share of cost | errors /100 moves | avg error |
|---|---|---|---|---|
| down a piece+ | 26.5% | 5.7% | 2.6 | 20.6 |
| down 1–2 pawns | 22.0% | 22.0% | 12.1 | 20.2 |
| even | 34.0% | 35.9% | 13.1 | 19.8 |
| up 1–2 pawns | 12.5% | **25.2%** | **21.4** | 23.1 |
| up a piece+ | 5.0% | 11.2% | 18.2 | **30.0** |

Down a piece+ is a floor (little expected score left to lose), not good play.

| other cuts (lost games) | share of moves | share of cost | errors /100 |
|---|---|---|---|
| queens on | 56.9% | **71.5%** | 14.1 |
| queens off | 43.1% | 28.5% | 7.8 |
| me < 20s | 11.4% | 10.3% | 9.1 (avg 24.5) |
| me behind 30s+ | 20.9% | 19.9% | 10.9 |
| clocks within 30s | 56.6% | 56.3% | 11.6 |
| me ahead 30s+ | 11.1% | 13.5% | 13.7 |
| opening (<= move 12) | 23.3% | 19.9% | 10.7 |
| middlegame | 30.7% | **45.9%** | 16.3 |
| endgame (npm <= 14) | 46.0% | 34.2% | 8.4 |

Biggest error per lost game (2,173 games): even material 41% (33% even with
queens on), ahead 33%, behind 26%; clocks within 30s 59%; queens on 75%.
Of the even-material ones, the engine had it 35–65% in 72%.

Clock imbalance is not where losses concentrate: rates are flat (9–14 per 100)
across clock states. Material lead + queens on is.

## Part 2 — visibility spectrum

Engine self-play (depth 10, 30 plies) from the position after the error, paired
with self-play from the position before it (the counterfactual best line).
Perceived material for me at each of my turns; the error "shows" at the first
turn where the error line is >= 2 pawns behind the best line and stays >= 1
behind. 2,600 random errors paired. Placebo: 247 non-error moves (|cost|<0.03)
run identically.

| tier | errors | cost | cost, lost games | avg | placebo |
|---|---|---|---|---|---|
| 1 lose material / mated within 3 moves | 24.4% | 33.3% | **40.8%** | 28.7 | 1.2% |
| 2 missed a material win available within 3 moves | 11.5% | 13.5% | 10.8% | 24.6 | 0% |
| 3 material only 4–15 moves out (either way) | 32.9% | 28.9% | 26.5% | 18.4 | 20.3% |
| 4 never material in 15 moves | 31.1% | 24.2% | 21.9% | 16.3 | 78.5% |

- Tier 3 is mostly horizon noise: good moves land there 20% of the time. Read
  it as "positional, with maybe a third real delayed tactics."
- Real opponents cashed in "material next move" errors by my next turn 71% of
  the time — 29% went unpunished.
- When up a piece+, 37% of errors are tier 1 (giving it back at once).
- About 2/3 of errors and ~55% of their cost give no material signal within
  three moves.

## Part 3 — "how I move after a mistake"

**After the opponent's mistake** (gift >= 10 pts, 11,391 cases): with no
material to grab (best SEE < 2 pawns), I give back >= 10 points 30–38% of the
time; with material to grab, 18–23%; baseline at the same engine win% with no
gift, 6–15%. Depth-16 re-check of 500 (250/arm): gifts survive 87–94%, and
among confirmed gifts give-back is **35.0% vs 17.9%**. Not depth noise.
Caveat: "nothing to grab" gifts often need one precise move, so this mixes
"didn't see it" with "saw something, couldn't find the move."

**After my own mistake:** next own move is an error 1.5–2.0x as often as
expected for its eval decile, in every visibility tier (tier 1 2.01 [1.72,
2.28]; never-material 1.76 [1.57, 1.93]; missed win 1.46 [1.27, 1.64]).
The spike does not need a visible mistake, so it is not reaction to noticing
one. Likely harder positions / same blind spot persisting.

## Caveats

Exploratory; segment cut points chosen once, not tuned. Depth 10 playouts;
15-move horizon. Move-level rows not independent (bootstrap by game where CIs
given). Perceived material ignores pieces en prise elsewhere on the board.

## Part 4 — how quick material losses happen, by material state (added same day)

Justin's question: the three "up 1–2 pawns" examples on the study page were
two pieces attacked more times than defended (one defended only by the king)
and one discovered attack. Typical for being ahead?

`scripts/visibility/mech.py` (depth 13 PV from the position after each of the
12,184 non-mate errors; output `data/vis_mechanism.jsonl.gz`) →
`mechan.py`. Quick material loss = engine line loses >= 2 (resolved) within
three moves: 3,487 errors. If the opponent's first move wins an en-prise piece
(SEE > 0): no defender / attacked by a cheaper piece / more attackers than
defenders (batteries counted) / other. Otherwise: discovered attack (a piece
other than the mover newly attacks a non-pawn of mine), fork / double attack,
or other. Checked by hand on the three study-page examples (all classed as
Justin read them).

| mechanism (all games) | down piece+ | down 1–2 | even | up 1–2 | up piece+ | all |
|---|---|---|---|---|---|---|
| piece with no defender | 30 | 36 | 35 | 35 | 38 | 35 |
| attacked by a cheaper piece | 7 | 10 | 11 | 11 | 10 | 10 |
| attacked more times than defended | 9 | 9 | 10 | 9 | 9 | 10 |
| discovered attack | 6 | 4 | 5 | 6 | 4 | 5 |
| fork / double attack | 3 | 5 | 5 | 5 | 2 | 4 |
| other (longer combinations, checks first, mate threats, promotions) | 45 | 35 | 33 | 35 | 36 | 35 |
| n | 156 | 705 | 1,154 | 899 | 573 | 3,487 |

Lost games only: same shape within 1–2 points. The mix of mechanisms does
not depend on material. What changes is how often a mistake is a quick
material loss: 24% of errors at even material, 29% up 1–2, 51% up a piece+.
King as the only defender among "attacked more times than defended": 11–14%
when even or behind, 19% up 1–2, 30% up a piece+ (only ~15 cases each when
ahead; suggestive, not established). Direct hangs when up 1–2: 45% a standing
threat already there before the move, 35% the piece just moved, 13% the move
took away a defender, 3% the move opened a line; same as other states.

## Part 5 — up-a-piece mistakes split three ways (added same day)

Justin read the three "up a piece" study examples as: didn't finish the tactic
after the opponent's blunder; a time scramble; firmly in control, then hung a
piece several moves later. Rules (first match wins), on the 1,363 mistakes made
at perceived material >= +3 (fullmove >= 6): my clock < 20s → scramble; first
own move at >= +3 (lead not banked yet; 28% of these still had the piece to
collect) → unfinished; lead 1–2 own moves old; lead 3+ own moves old. All three
study examples land where Justin put them.

| | all games: errors / cost | lost games: errors / cost |
|---|---|---|
| time scramble (< 20s) | 26% / 27% | 22% / 22% |
| lead not banked yet | 14% / 15% | 17% / 18% |
| lead 1–2 moves old | 16% / 16% | 19% / 19% |
| lead 3+ moves old | 44% / 42% | 43% / 40% |

First up-a-piece mistake in each of 336 lost games: scramble 14%, unbanked
28%, 1–2 moves 22%, 3+ moves 35%. Scramble share is threshold-sensitive (<10s
9%, <15s 20%, <30s 35% of all up-a-piece mistakes).
