# Pre-spec: does opening study dose predict the opening edge?

Written 2026-10-23, **before any per-family value of any metric below was
computed.** Committed before `features.py` was run in this session.

## What had already been seen

Stated so the reader can judge how blind this is:

- The pooled opening-bucket rates from "Opponents as a same-rating benchmark"
  (me 3.85% vs opponents 4.30% P1, moves 1–12, all families together).
- The repeated-opening-error list in "Opening errors are almost never
  repeats", which names Englund trap lines among the repeats.
- The thread 8a post-hoc note that `Black vs 1.d4` separates descriptively
  on book depth (not a finding).
- The `openings.py` clock table: Englund spend climbs from move 6.

No family-level error rate, for either player, had been computed.

## Hypothesis (Justin's, stated before any output)

Justin's study history, in his words, 2026-10-23: **London — a lot of
videos; Caro-Kann — a medium amount, and he does not understand it well (no
sense of how to play the Advance differently from the Exchange); Englund —
never watched a video.** If opening study is what produces the opening edge,
the edge over same-rated opponents should be largest in the London, smaller in
the Caro, smallest (or absent) in the Englund. If repertoire narrowness alone
produces it, the three should look alike, since all three are played the same
way every time.

## Scope

- Lichess only, the six settled blocks (2024 H2, Q1–Q4 2025, 2026 to
  2026-08-19), 3+2 and 5+0 — identical to `buckets_prespec.md`.
- **Hard gate: no game on or after 2026-09-03** (group F treatment block).
- Gates: `features.py` on Justin gives 4,691 games / 155,192 own-move rows;
  on the opponent (names rewritten to `OPPONENT`, as in `vsopp`) the same
  4,691 games / 155,008 rows.

## Families (from the moves actually played)

- **London**: Justin is White, 1.d4, Black's reply is anything but 1…e5.
- **Caro**: Justin is Black, 1.e4 c6.
- **Englund**: Justin is Black, 1.d4 e5.
- Everything else is excluded from the primary test.

## Moves counted

Own moves with `fullmove <= 12` whose `cp_before` is not a mate score, for
Justin and for the opponent in the same games. (Departure from the `buckets`
Opening bucket: the M2 mate-danger scan is not re-run, so mate-danger
positions in moves 1–12 are included rather than removed. They are a small
share of the opening and fall on both sides of the board.)

## Metric

- **P1**: share of moves with `wp_error >= 0.15` (as in `buckets`).
- **Edge** in family F: `D_F = P1(Justin) − P1(opponent)`, same games, same
  move window. Negative = Justin errs less. Comparing against the opponent in
  the same games is the control for the Englund simply being a worse opening:
  objectively worse positions raise error rates for both players.

## Test

- **Primary**: `D_Englund − D_London > 0` (the edge is smaller in the
  Englund). Game-level bootstrap, games resampled within family, both
  players' moves travel with their game, 10,000 draws, seed 23. **Passes if
  the one-sided bootstrap p < 0.01.**
- **Secondary**: `D_Caro − D_London > 0`, same machinery, same 0.01 bar;
  and whether the three point estimates fall in the predicted order
  (descriptive).
- **Exploratory, not tested**: P2 (mean `max(wp_error, 0)`) for the same
  contrasts; Caro split into Advance (3.e5) and Exchange (3.exd5); the
  Englund with Justin as White (1.d4 e5); raw rates for each side.

## Resolution

Reported with the result: the size of difference in `D` the primary contrast
could detect at 80% power, from the bootstrap standard error.

## Known weaknesses, stated before the result

- Study dose is self-reported and three levels; it is confounded with
  everything else that differs between the openings (sharpness, how often
  opponents know them, colour). A pass would be consistent with the study
  hypothesis, not proof of it.
- Opponents are likely least familiar with the Englund, which pushes
  `D_Englund` toward Justin's favour — against the prediction.
