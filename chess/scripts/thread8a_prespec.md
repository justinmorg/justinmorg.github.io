# Thread 8 channel A — pre-specification

Written **before** any output was inspected. Committed as its own file so the
rule cannot be quietly edited after the fact. Run by `thread8a.py`.

## Question

Does leaving the opening book early produce a worse position, controlling for
opening family?

## Prior

**Null.** Every opening-phase test in this README has come back null, eval at
move 12 is fine, and the gaps `openings.py` found cost seconds rather than
centipawns. Stated up front so a null is not retrofitted as "expected".

## Scope

- **Lichess only.** `openings.py` excludes chess.com by design; the CC-2026
  block ends 2026-04-01 and so contributes zero games to the test window
  regardless.
- Blocks `Q3-2025`, `Q4-2025`, `2026`; `--tc 180+2,300+0`.
- **Train window** (builds the node table): 2025-09-01 → 2026-04-30.
- **Test window** (games actually scored): 2026-05-01 → 2026-08-19.

Held-out because book status is defined partly *by* time, and regressing a
time-derived predictor on a time-derived outcome is circular in exactly the
direction the hypothesis predicts.

## Exposure

Book depth per game = consecutive own moves from move 1 that are book moves,
using `openings.report_depth`'s definition unchanged (`min_reps` 25, share
≥ 0.90, mean spend < 3.0s, plies 1–2 time-exempt), against a node table built
on the **train** window only.

## Family (the control that matters)

As `report_depth` defines it — White: `White 1.d4 <opponent reply>`; Black:
`Black vs 1.<opponent first move>`. Colour is nested inside family by
construction. Families with **≥ 30 test-window games** are included; smaller
families are reported and dropped.

## Outcomes (three)

- **O1, primary** — `cp_after` of own move 12, player POV, `mate_flag == 0`.
  Chosen over middlegame-entry eval because `cp_after` of an *own* move carries
  no POV trap (see the thread 2 note on side-aware entry eval).
- **O2** — binary, O1 ≤ −100cp.
- **O3** — binary, reached ≥ +200 in the middlegame (`peak >= 200`).

## Test

Within-family Spearman rank correlation between book depth and outcome, pooled
as a sample-size-weighted mean across included families. p from a stratified
permutation test: shuffle book depth **within family**, 10,000 draws, seed 23.
One game = one unit, so no clustering correction is needed.

Rank correlation rather than a shallow/deep split, chosen to avoid a threshold
that would be picked after seeing the depth distribution.

## Decision rule

A **positive finding requires p < 0.01 on O1**, given three outcome columns.
O2 and O3 are reported alongside; a positive on either without O1 is logged as
a **flag, not a finding**.

## Secondary, descriptive only

Within-family median split (shallow vs deep), mean O1 per arm. For
interpretability. **Not the test**, and not to be quoted as one.

## Covariate check

Mean `opp_elo` against depth within family. If the pooled
Spearman(depth, opp_elo) exceeds 0.10 in absolute value, re-run stratified by
family × opponent-Elo tercile as a robustness check.

## Resolution

Report the detectable-at figure for the **actual held-out n**, at 80% power and
alpha 0.01, two-sided, on the median-split arms. The README's published
45cp/64–90cp table is computed on all 1,772 games in the full window and
therefore **overstates the resolution of this held-out test**; the real figure
is whatever the test window supports and must be reported with the result
either way. A null is worth nothing without its resolution attached.

## Validation gates (hard-exit)

1. `openings.gate` — clock arithmetic reproduces moves 16–20 mean spend
   (8.4s at 180+2, 7.8s at 300+0).
2. Full-window rebuild reproduces the published `openings.py` figures:
   1,772 games, in-book mean 1.38s, first-out-of-book mean 2.53s, `1.d4` as
   White 881/882.
3. `features/games.csv` is the 5,636-game eight-block run.
4. Full-window eval@12: n ≈ 1,643, sd ≈ 265cp.
