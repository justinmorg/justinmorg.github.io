# Block homogeneity of the level-endgame score — pre-specification

Written **before** any per-block output was inspected, and committed as its
own file so the rule cannot be quietly edited afterwards. Run by
`eglevel.py`. Same discipline as `pawnpiece_prespec.md` and
`thread8a_prespec.md`.

## Question

The README publishes one number for games entered into the endgame level:
**42.7% [39.4, 46.1] over 774 games**, pooled across the seven-block run. Is
that one number, or several? Concretely: do the seven blocks that make up the
774 differ from each other on this metric by more than game-level sampling
noise, and does the held-out Q4 2025 block land where the pooled figure says
it should?

## What has already been seen, stated so it cannot leak

Published figures adjacent to this metric that were in hand when this was
written:

- pooled 42.7% [39.4, 46.1], n = 774 (seven blocks);
- by site: Lichess 641 at 43.1%, chess.com 133 at 41.0%;
- by format, Lichess only: 3+2 529 at 42.1% [38.0, 46.0], 5+0 112 at 47.8%
  [38.4, 57.1];
- the *even-middlegame* bucket (a different population, 442 games) is
  published per block as 42.6 / 43.8 / 40.1 / 42.1 / 36.7%;
- `material.py`'s level curve at its material crossings: "six of seven blocks
  fall between 40.8% and 46.4%".

**No per-block value of the endgame-entry level score has been published or
looked at.** Q4 2025's value for this metric has never been computed.

## Prior

**Null — the blocks do not differ.** Every other outcome-type rate in this
corpus has come back homogeneous across blocks (hanging material p = 0.86,
`hung it myself` p = 0.86, conversion from won positions flat at 62.5–65.6%),
and the adjacent even-middlegame per-block figures above sit inside a 7-point
band on small n. Stated up front so a null is not retrofitted as expected.

## Metric

Per game: **score** (1 / 0.5 / 0, player POV) in games whose endgame-entry
eval is **level**. Definitions imported, not restated:

- endgame entry = first position with `fullmove > 12` and light non-pawn
  material ≤ 14, checked on **every** ply (the endgame-entry ply bug in the
  README: entry is often the opponent's move). This is `features.py`'s
  `eg_entry_cp` / `eg_entry_ply`.
- level = `outcomes.bucket_of(eg_entry_cp) == "level (-100..+100)"`, i.e.
  −100 < cp ≤ +100, player POV. Import `bucket_of`; the README records that
  reimplementing the boundary moves four games.

One game = one observation. Games with no endgame entry are outside the
population, by construction.

## Scope

Corpus default: `--tc 180+2,300+0`, both sites, from the **eight-block**
`features.py` run (5,636 games / 186,191 own-move rows). The seven-block
subset inside it must reproduce the published 774 / 42.7% exactly (gate 2).

## Blocks

**Homogeneity test — seven blocks**, the scope of the published 42.7%:
`2024H2`, `Q1-2025`, `Q2-2025`, `Q3-2025`, `2026`, `CC-2024Q4`, `CC-2026`.

**Held-out replication block — `Q4-2025`.** Excluded from the homogeneity
test; tested separately against the pooled seven-block rate, below. It was
annotated in Aug 2026 and folded into `outcomes.py`, but this metric has never
been computed on it, so it is genuinely unlooked-at for this purpose.

## Permutation scheme

`blockstats.py shuffle`'s scheme, re-implemented on `games.csv` because
`blockstats.py` does not carry `eg_entry_cp`:

- unit = game; label = block; the population is the level-endgame games only;
- statistic = **spread** (max block score − min block score), plus the
  minimum-block and maximum-block statistics as `blockstats.py` prints them;
- 20,000 label shuffles across blocks, seed 23; p = (count + 1) / (n + 1).

Q4 replication: add Q4's level-endgame games to the pool, shuffle the
Q4-vs-rest label at the game level, 20,000 draws, seed 23; **two-sided** p on
|Q4 score − pooled-other score|. Two-sided because Q4 is a pre-declared
replication block, not a block singled out for being extreme in a known
direction — the opposite situation from the June 2025 dip.

## Decision rule

**Homogeneity.** "Blocks differ" requires **spread p < 0.05** on the seven
blocks. The minimum- and maximum-block p-values are reported but do not
decide, since no block was singled out in advance. A result at 0.05 ≤ p is
"no block differs at the resolution below".

**Replication.** "Q4 replicates" if its two-sided p ≥ 0.05. "Q4 fails
replication" if p < 0.05 — reported as a **flag**, because, as the resolution
section says, a block of Q4's size can only fail this test by a very large
margin, and one small block is the shape of every retracted finding in the
README.

One primary test (spread) and one replication read. Nothing else in this
script decides anything.

## Resolution — to be reported with the result, whichever way it lands

Computed by simulation at the **actual** per-block n of level-endgame games,
not quoted: draw block scores from a common rate of 0.427, apply the same
spread test, and report the uniform per-block shift (one block moved by δ, the
rest at 0.427) that the spread test detects at 80% power, for the smallest and
the largest block. A null is worth nothing without this attached.

For Q4: at ~14% of games entering the endgame level (774 / 5,404), 232 games
gives roughly **30–35 level-endgame games**. Against a fixed 42.7%, 80% power
at α = 0.05 two-sided detects a difference of about **24 percentage points**
(42.7% → ~19% or ~67%). Stated now: **Q4 cannot distinguish 42.7% from 35% or
from 50%.** Its replication read is a coarse sanity check, not a test of the
figure.

## Selection-bias caveat — this must travel with every number

**The population is conditioned on reaching a level endgame**, and reaching
one is not random. The README's `material.py` section already shows the
benchmark for a level position is not 50% — wins end early and losses run
long, so any "still alive at move N" population scores below 50% before the
eval is mentioned. This test inherits that: a block-to-block difference in
*who reaches a level endgame* would read as a block-to-block difference in
*endgame technique*, and the design cannot tell them apart.

The specific hazard for the replication block: Q4 2025 has an elevated share
of games that simplify before move 13 (13.4% against 6.4–9.1% elsewhere — the
untested flag in "Where Q4 2025 lands"). Those games enter the endgame at move
13 by definition and are queenless middlegames rather than endgames in any
technical sense. So Q4's level-endgame set is drawn by a different selection
than the other blocks', and whatever it scores is partly that. A descriptive
split by entry ply (≤ 30 vs later) is printed for all blocks so the reader can
see it; it is **not** part of the decision rule.

Same caveat in plain words: a level endgame is not assigned at random, it is
arrived at, and the road there differs by block. This test compares the
destinations, not the roads.

## What this result can and cannot change about the drill queue

**The drill queue does not move on this result in either direction. Stated
before the number exists.**

- **Homogeneous (p ≥ 0.05):** confirms that pooling the 774 was legitimate
  and the 42.7% is one number. Nothing changes. The endgame track's priority
  was already lowered by the `material.py` benchmark argument (42.7% is
  roughly par for the material on the board), and this does not touch that
  argument.
- **Heterogeneous (p < 0.05):** a **flag**, not a finding. It would mean the
  pooled figure is averaging over blocks that differ, and the first question
  would be selection (the caveat above), not technique. It would need a
  mechanism-free replication on the next annotated block before it changed
  anything, and it would still not say *what* to train.
- **Q4 in either direction:** cannot reorder anything on ~33 games.

Also binding, and independent of this test: the pre-registration froze the
card set and protocol for the duration of the current treatment block, and
any change restarts the block. No drill change is admissible until that block
resolves, whatever this test says.

The one outcome that would earn a *pre-specified follow-up* (not a queue
change): the `2026` block — the most recent, and the only one carrying 5+0 —
being the extreme block at its own end with p < 0.01. That would be a
format-or-era flag worth a pre-registered test on the next block. Anything
weaker is noise until replicated.

## Validation gates (hard-exit)

1. `features/games.csv` is the eight-block run: 5,636 games; and
   `moves.csv.gz` has 186,191 rows.
2. Restricted to the seven published blocks: 5,404 games; endgame-entry
   buckets **1,073 / 401 / 774 / 1,443**; level score **42.7%** to one
   decimal.
3. Seven-block level row by site: Lichess **641 at 43.1%**, chess.com
   **133 at 41.0%**.
4. Seven-block level row, Lichess only, by format: 3+2 **529 at 42.1%**,
   5+0 **112 at 47.8%**.
5. `block` and `gid` read as strings (`dtype={"block": str, "gid": str}`) —
   the integer-parse trap that silently drops a third of the `2026` block.
