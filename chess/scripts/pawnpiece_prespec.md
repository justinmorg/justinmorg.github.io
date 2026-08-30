# Pawn moves vs piece moves — pre-specification

Written **before** any output was inspected. Run by `pawnpiece.py`.

## Where the hypothesis came from

Group R note theme §2: several notes describe a committal pawn move whose
danger came from geometry the move itself created — `3eLsCWEU` (17.f3 weakens
e3), `SXNKVcS7` (14.f4 opens Nxe3 forking queen and rook), `KcwgSovn` (21.g4
and the queen ends up trapped). A pawn move cannot be taken back and changes
the pawn skeleton, so the position after it is *least* like the position that
was scanned. Prediction: **own pawn moves carry a higher blunder rate than own
piece moves**, after controlling for how hard the position was.

**Selection note.** The hypothesis came from 40 notes chosen as the costliest
hot-zone drops, so it is post-hoc *with respect to those 40 positions*. The
test below runs on ~108k rows across seven blocks, which is close to
independent of them — 40 rows cannot drive that rate. It is not fully
independent and the secondary hot-zone cut is where the overlap concentrates,
which is why that cut is labelled exploratory.

## Correction to the README

The group R write-up said "`features.py` already carries the move played."
**That is wrong.** `moves.csv.gz` carries `opp_prev_san` — the *opponent's*
previous move — and no column for the player's own SAN. This script therefore
re-walks the annotated PGNs to recover own-move SAN and merges on
`(gid, ply)`. The README claim is corrected where it appears.

## Prior

Genuinely uncertain, with a weak positive lean. Stated honestly: every
notes-derived hypothesis this project has tested has come back null or
reversed (H1, the June dip, the difficulty interaction, thread 7). That is the
base rate this one is running against.

## Scope

The **seven-block** run — 5,404 games, 178,684 own-move rows — matching the
`oppmove.py` precedent whose method this copies, so its published rates can
serve as a gate. Own moves, `fullmove > 12`, non-mate. Blunder =
`drop_cp >= 200`, at the +2 line and inside the depth-12 reliable band.

## Exposure

From own-move SAN:

- **pawn** — SAN begins with a file letter (a–h), i.e. no piece letter.
- **piece** — SAN begins with N/B/R/Q/K.
- **castling** — `O-O` / `O-O-O`. **Excluded** and reported separately; it is
  neither, and it is structurally unlike both.

Promotions count as pawn moves (they are pawn moves).

## Controls

Direct standardization, `oppmove.py`'s treatment. Stratum axes:

move band (13–18 / 19–25 / 26–35 / 36+) × `n_legal` quartile × eval bucket ×
`in_check` × `tc` × **own move was a capture**.

Two deliberate choices, declared now:

- **`own_is_capture` is a stratum axis.** Pawn captures and piece captures have
  very different blunder profiles, and the recapture effect is already
  established. Without it this would partly measure captures.
- **`in_check` is included** and, unlike in `oppmove.py`, is not collinear with
  the exposure — in check you can still move either a pawn or a piece, though
  king moves are over-represented. `n_caps_avail` is dropped to keep the
  stratum count from exploding; it is weakly informative and correlated with
  `n_legal`.

Report the share of rows retained after empty strata are dropped.

## Test

Within-stratum permutation of the pawn/piece label, 10,000 draws, seed 23,
two-sided. Game-clustered bootstrap for the interval — moves inside one game
share an opponent, a clock trajectory and a position, so row-level intervals
would be too tight.

## Decision rule

**Positive finding requires p < 0.01 on the standardized pawn − piece
difference in blunder rate, in the predicted direction (pawn worse).** A
result significant in the *opposite* direction is reported as such and is not a
confirmation of anything.

## Secondary, exploratory and labelled as such

The same contrast restricted to the hot zone (moves 13–25, `npm_light >= 13`),
where the R notes came from. **Not** part of the decision rule; this is the
cut with the most overlap with the positions that generated the hypothesis, so
a positive here alone is a flag, not a finding.

## Validation gates (hard-exit)

1. Features run is the seven-block one: 5,404 games / 178,684 rows.
2. In-scope row count is 108,151, matching `oppmove.py`.
3. `oppmove.py`'s published raw crosstab reproduces: check 7.95%, capture
   8.46%, pawn_break 10.44%, quiet 10.16%. Computed from columns this analysis
   does not use, so it is an independent check on the input.
4. SAN merge covers ≥ 99.5% of in-scope rows.
