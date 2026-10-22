# Pre-spec: error rate by position bucket, over time

Written 2026-10-22, **before any per-block value of any metric below was
computed.** Pooled (all-blocks) counts per bucket had been looked at while the
design was being argued over; those say where errors happen, not whether
anything changed, which is the only question this tests. Committed before the
mate-danger scan was run on the full corpus.

## Question

Has the error rate moved over time inside position categories that map to
study areas (openings, middlegame by eval state, endgame by eval state, mate
positions)? The plateau since mid-2025 was read off whole-game and move-band
rates; this asks whether that flatness hides movement in one category.

## Scope

- Lichess only, the six settled blocks: 2024 H2, Q1–Q4 2025, 2026 (to
  2026-08-19). chess.com excluded (different pool; not a time series).
- **Hard gate: no game dated on or after 2026-09-03** (group F treatment
  block — no interim look). The script exits if one appears.
- Primary scope: corpus default, 3+2 and 5+0. Robustness scope: 3+2 only.
  (3+2-only loses 2026 May–Aug, which is why it is not primary.)
- Own moves, from `features.py` run on exactly those six blocks; gate is
  4,691 games / 155,192 own-move rows.

## Buckets

Judged on the position **before** the own move. Rules applied in order, first
match wins, so the partition is exclusive; the last rule catches everything,
so it is exhaustive. Script asserts both.

1. **M1 mate for me** — `cp_before` is a mate score for me.
2. **M3 mate against me** — `cp_before` is a mate score against me. Cannot
   err by construction; counted, not tested.
3. **M2 mate danger** — not M1/M3, and any of:
   a. not in check, and after a null move, depth-12 Stockfish 16 reports a
      forced mate for the opponent (a standing mate threat);
   b. some legal move lets the opponent mate in one (board logic, no engine);
   c. in check, and some legal move leads to a position where depth-12
      Stockfish 16 reports a forced mate for the opponent.
4. **Opening** — `fullmove <= 12`.
5. **EG ahead / 6. EG level / 7. EG behind** — `npm_light <= 14`; split by
   `outcomes.bucket_of` bands: cp > +100 / −100 < cp <= +100 / cp <= −100.
8. **MG winning / 9. MG level / 10. MG losing** — otherwise; cp >= +150 /
   −150 < cp < +150 / cp <= −150 (the group P gate at the top).

M2 gate: the scan must flag at least the 1,055 of 1,518 known
walked-into-mate positions that rules (a)+(b) flagged in the coverage test
(rule c can only add).

## Metrics (per own move, within bucket)

- **P1 error rate**: share of moves with `wp_error >= 0.15` (Lichess
  win-probability curve, fixed; 15 points = Lichess's "blunder" line).
- **P2 win chance lost per move**: mean of `max(wp_error, 0)`.
- Secondary, for continuity with published tables: `drop_cp >= 200`.
- Descriptive only: each bucket's share of moves per block (exposure), and
  mean `cp_before` per block (composition).

## Test

Per bucket (nine testable: all but M3) and per primary metric (18 tests):

- Statistic: weighted least-squares slope of the block-level metric on block
  midpoint date (in years), weights = moves in that bucket and block.
- Null: game-level shuffle of block labels (block game counts preserved),
  20,000 draws, seed 23, two-sided.
- Multiple comparisons: Holm–Bonferroni across all 18 at family alpha 0.05.

**A bucket counts as having moved only if** it passes Holm on the primary
scope **and** the 3+2-only slope has the same sign. Reported alongside every
result: 2024 H2 vs 2026 endpoint difference with a game-level bootstrap 95%
interval (2,000 resamples, seed 23) — that interval's half-width is the
stated resolution.

## Prior, written down

The published series says moves 26+ improved ~26% relative from 2024 H2 to
2026 and nothing else moved. Expected: any movement sits in the endgame
buckets; the opening and middlegame buckets are flat. A result that instead
shows a middlegame bucket improving would contradict the move-band table and
gets checked for composition before it is believed.

## Not affected

The group F pre-registration is untouched: these are pre-intervention blocks
only, and nothing here changes the card set, protocol or outcome.
