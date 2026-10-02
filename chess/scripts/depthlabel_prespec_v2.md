# Detection depth vs think time — pre-specification, version 2

Written after the version-1 gate G2 failed and **before the primary test was
run under either version**. Version 1 (`depthlabel_prespec.md`) is left
unedited; this file amends it. Everything not changed here stands as written
in version 1.

## What v1 produced (the only output seen)

- G1 passed: 8,269 / 10,304 = 80.3% confirmed at depth 12 (gate 75%).
- G2 failed: 1,746 / 2,150 = 81.2% of SEE-flagged blunders classed shallow
  (gate 85%); `hung_it_myself` 85.2% (n 809), `missed_their_threat` 78.8%
  (n 1,341).
- Diagnosis of the 404 G2 misses, engine columns only (no `spend` touched):
  detect depth 4 / 8 / 12 = 138 / 159 / 107. Median `loss2` among them 123cp;
  254 of 404 have `loss2 >= 100`. 88 have both `loss1` and `loss2` < 50 —
  spot checks show the SEE flag and the actual refutation diverge in these
  (consistent with the 10.4% H-label false-positive rate in the group F audit).
- Alternative cutoffs on the G2 rows, computed while diagnosing:
  `max(loss1, loss2) >= 100` → 93.1%; `>= 150` → 88.1%.

So the shallow search mostly *sees* the material falling but scores it short
of the 200cp blunder line. The defect is the cutoff, not the axis.

## Amendment

- **shallow** := `loss1 >= 100 or loss2 >= 100` (one pawn at depth 1–2).
- **mid** := not shallow and `loss4 >= 200`; **deep** := otherwise.
- **confirmed** unchanged: `loss12 >= 200`.
- **G2 is demoted to calibration.** The 100cp cutoff was chosen having seen
  its G2 value (93.1%), so G2 can no longer test the instrument. It is
  reported, not gated on. G1 stands as passed.
- 100cp rather than 150cp: the round one-pawn line, and the smaller of the
  two values examined; not tuned further. Stated so it is not mistaken for an
  optimised choice.

## Unchanged

Population, confirmation rule, strata, standardization, 4,000-shuffle
stratified permutation, game bootstrap, the split-half requirement, S1–S3,
and the prediction (shallow share higher among fast ≤2s than slow ≥8s
blunders). **The primary contrast has not been computed under any cutoff.**
