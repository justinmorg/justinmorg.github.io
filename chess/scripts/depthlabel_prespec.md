# Detection depth of blunders vs think time — pre-specification

Written **before** any depth-label output was inspected, and committed as its
own file so the rule cannot be quietly edited afterwards. Run by
`depthlabel.py` (engine pass) and `depthlabel_analyze.py` (analysis). Same
discipline as `eglevel_prespec.md`, `pawnpiece_prespec.md`,
`thread8a_prespec.md`.

A 232-position timing benchmark was run before this file was written; its
output was kept as the start of the resumable run and was **not** read.

## Question

The multi-PV work closed the solution-narrowness confound but left human
difficulty unmeasured (`n_within_100` scores a forced recapture as maximally
hard). This tries a different, cheap axis: **at what engine search depth does
the blunder become visible?** A move that is already ≥200cp worse than best at
depth 1–2 loses to something quiescence search resolves — material falling to
captures. A move that only looks bad at depth 8–12 loses to something quieter
or deeper. That is engine difficulty, not human difficulty; the test below is
whether it tracks anything in Justin's behaviour.

## What has already been seen, stated so it cannot leak

- Think time: blunder rate rises monotonically with spend; standardized fast
  (≤2s) 7.29% vs slow (≥8s) 12.78%.
- Group P floored hits: median spend 8.0s vs 6.0s for eligible moves; only 10%
  of floored hits on moves ≤2s.
- Multi-PV: fast moves sit on narrower positions (51% only-move vs 31%), gap
  unattenuated within narrowness bins.
- ~76% of blunders in won positions are judgment rather than hanging material;
  the "quiet punishment" 43% that H2 doesn't cover.

**No detection-depth value has been computed for any position before this.**

## Prior

**Weak, roughly a coin flip with a lean toward the prediction.** For it: the
mechanism section describes the slow-move failures as considered quiet moves
punished quietly. Against it: hanging-material hits — the archetypal shallow
blunder — skew *slow* (median 8s), which pushes the other way. Stated so a
null or reversal is not retrofitted as expected.

## Population

Own moves, `fullmove > 12`, `mate_flag == 0`, `0 <= spend <= 60`,
`drop_cp >= 200` — the README think-time scope, restricted to blunders.
Seven-block `features.py` run (`--tc 180+2,300+0`, both sites): **10,304
blunders**, 2,822 fast (≤2s), 3,595 slow (≥8s), 3,887 between.

## Labels

Per position, per d ∈ {1, 2, 4, 8, 12}, empty hash before every search:
`loss_d = best_d − played_d` (mover POV, mate → ±10000).

- **confirmed**: `loss12 >= 200`. Unconfirmed rows (the stored drop is a
  depth-12 eval of each side's position, so effectively one ply deeper, and
  can disagree) are counted, reported and excluded.
- **detect depth**: smallest d with `loss_d >= 200`.
- **class**: `shallow` (detect ≤ 2) / `mid` (4) / `deep` (8 or 12).
- **non-monotone**: visible at some d, invisible at a larger d < 12. Counted
  and reported; the first-crossing rule is applied regardless.

## Gates — if either fails, stop; the primary test is not interpreted

- **G1 confirmation.** ≥ 75% of the 10,304 confirmed at depth 12. Below that
  the recompute disagrees with the corpus too much to label its blunders.
- **G2 validity.** Among confirmed blunders with `hang_label != none` (SEE
  says material is immediately lost), ≥ 85% classed `shallow`. If not, depth
  1–2 is not detecting what this design says it detects.

## Primary test

**Prediction: the share of `shallow` blunders is higher among fast (≤2s)
than slow (≥8s) blunders.**

Statistic: fast − slow difference in shallow share, **directly standardized**
over strata of format × move band (13–25 / 26+) × `n_legal` quartile
(quartiles of the confirmed population) × `n_caps_avail` (0 / 1–2 / 3+) ×
`in_check`, weights = pooled count of the stratum among fast+slow rows;
strata lacking either group are dropped and the dropped count reported.
Standardization is needed because fast and slow moves are played in
different positions (more captures available, more legal moves), and those
plausibly change how deep a refutation sits regardless of time spent.

Significance: stratified permutation of the fast/slow label within strata,
4,000 shuffles, two-sided. **Supported** iff p < 0.05 and the sign is as
predicted. Bootstrap 95% interval over games reported alongside.

Robustness, required before calling it a finding: split games 50/50 by a
seeded hash of `gid` (seed 20261002); the standardized difference must have
the predicted sign in **both** halves. Three apparent interactions in this
corpus have failed held-out replication; this is the guard.

## Secondary (reported, not decision-bearing)

- **S1.** Same statistic restricted to `hang_label == none` — blunders SEE
  does not flag. This is where the label could add information the corpus
  lacks; if the primary result is only the hang/no-hang mix across spend, S1
  will show it.
- **S2.** Class distribution (shallow / mid / deep) across all seven spend
  bands of the think-time table, unstandardized.
- **S3.** Counts: unconfirmed, non-monotone, by format.

## What this cannot show

Human difficulty. A refutation the engine needs depth 8 to see may be obvious
to a person (a positional collapse) and a depth-1 one may be invisible (a
long-range capture). Nor causation: spend responds to the position. A positive
result says the label tracks *something* in how these errors are made, which
is what would justify using it as a drill-selection or reflection filter. A
null says engine depth does not separate Justin's fast and slow errors and
should not be used that way.
