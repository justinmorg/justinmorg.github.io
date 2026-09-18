# Q4 2025 as a replication block for the flat hanging-material rate — pre-specification

Written **before** the 0.05-floor result on Q4 2025 was computed. Short,
because the definitions are the pre-registration's and are not restated or
altered here; this file only fixes how Q4 is read as a replication block.

## Question

Does Q4 2025, read as a held-out block, replicate the finding that the
floored hanging-material rate per eligible winning-middlegame move is flat
across the settled era (~4.3–5.2% at the 0.02 floor, "~4.7%" on the 3+2
table)?

## What has already been seen

At the **0.02 floor** Q4 is already published: 693 eligible, 4.33%
[2.89, 5.92] at 3+2, inside the six-block shuffle at p = 0.86. That run is
re-executed here only as a tripwire (it must reproduce spread 0.92 pp,
p = 0.86 to Monte Carlo noise). **At the pre-registered 0.05 floor, and at
the corpus-default 3+2/5+0 scope, no block's rate has been computed in this
repository.** That is the unlooked-at quantity this file governs.

## Definitions — the pre-registration's, unchanged

- Denominator: `hanging.py`'s eligible winning-middlegame move — own move,
  `fullmove > 12`, light npm > 14, eval ≥ +150 player POV.
- Numerator: SEE ≥ 150 hit clearing the win%-error floor of **0.05**.
- Scope: `--tc 180+2,300+0`, **Lichess only**, the six settled blocks
  (2024 H2, Q1–Q4 2025, 2026).
- Tool: `blockstats.py shuffle --metric hang --floor 0.05 --seed 23`,
  20,000 draws. `--floor` is new (default 0.02, so every published table is
  unchanged); it is the only tooling change and it does not touch eligibility.

## Test and decision rule

Q4 is a **pre-declared held-out block, not one singled out for being
extreme**, so the read is two-sided: the single-block p at whichever end Q4
lands (`blockstats.py` prints both), doubled. **Q4 replicates** if that
two-sided p ≥ 0.05. **Q4 fails replication** if p < 0.05 — reported as a
flag, since at ~690 eligible moves it can only fail by a wide margin (below).
The six-block spread p is reported as the "does any block differ" question,
as in the README.

`hungself` is reported alongside at the same floor. No decision rides on it.

## Resolution

At ~693 eligible moves against a baseline near 4.5%, 80% power at α = 0.05
two-sided detects a difference of about **±2.2 percentage points** — i.e.
Q4 could be seen to differ only if it were below ~2.3% or above ~6.7%. The
README's own volume rule says a block under ~450 games "cannot distinguish
anything from the existing 4.3–5.2% band". Q4 is 232 games. Stated now: a
replication here means "not wildly off", not "confirmed to the point".

## Interaction with the pre-registration

This computes the **baseline** blocks at the pre-registered floor. It does
**not** compute anything on the treatment block (games after 2026-09-03),
which is not in the repository, so the no-interim-look rule is untouched.
The pre-registration says the baseline is recomputed at test time; this run
is a preview of that arithmetic, not a substitute for it.
