# chess

Canonical game corpus and analysis tooling for Lichess account `jamorgan`.

This folder is **not a published site** — unlike the other top-level folders in
this repo, there's no `index.html` here. It lives in the repo so the corpus and
scripts are findable and updatable from any session. (Pages does still serve the
files at `https://justinmorg.github.io/chess/...` since it publishes the whole
repo root; nothing here is secret, but nothing here is meant to be browsed
either.)

## Explaining results — read this before writing any of them up

**This README is dense on purpose. Conversation must not be.**

The file is written for a future session picking this up cold, so it is packed
with caveats, scope lines and p-values, and that density is doing real work
here. It does the opposite of real work when the same register gets used to
explain a result to Justin, who has said plainly that these explanations are
often hard to follow. **Two registers. Keep them separate.** If an explanation
reads like this file, it is wrong for the conversation.

Rules for explaining any result:

1. **Lead with the answer in one plain sentence, before any number.** "Leaving
   the opening book early does not make your positions worse" — not "O1 returns
   rho = −0.056 at p = 0.14."
2. **Say what it means for how he plays or studies.** Every result ends with
   "so what". Often the honest answer is "this changes nothing you do," and
   that is a fine answer — but say it, don't leave it to be inferred.
3. **Translate every number into something physical.** 80cp is "about
   four-fifths of a pawn." 200cp is "a rook for a knight, roughly." A p-value
   is "how likely this is to be a coincidence." A rank correlation near zero is
   "the two things don't track each other."
4. **Define the jargon in the conversation, every time, not just here.** cp,
   rho, permutation test, standardization, held-out, stratified, floored,
   eligible move. Familiarity with the README is not familiarity with these
   terms, and re-defining them costs one clause.
5. **Say what the test could and could not have caught, in plain units.** "If
   it cost most of a pawn I'd have seen it; if it costs a tenth of a pawn I
   couldn't tell." A null with no resolution attached is not an answer, and a
   resolution stated only in centipawns is not an explanation.
6. **Explain why a control was needed, not just that it was applied.** "Which
   opening you face isn't your choice, and some are easier — so I only compared
   games within the same opening." One sentence, and the whole design becomes
   legible.
7. **If he would have to ask "so what did you find?", the write-up is not
   finished.** That question is the failure signal. Do not answer it by
   restating the table more slowly; rewrite the explanation from the answer
   outward.

The caveats still travel — this project's whole asset is that its numbers
survive re-testing, and hiding a limitation to make an explanation cleaner
would be worse than any amount of density. The requirement is to state
limitations in plain words, not to drop them.

## Layout

```
chess/
├── data/
│   ├── jamorgan_blitz_2026_analyzed.pgn.gz   canonical corpus (gzipped)
│   ├── jamorgan_blitz_2025_raw.pgn.gz        2025 games, clocks only, NO evals
│   ├── jamorgan_blitz_2023_2024_raw.pgn.gz   2023-24 games, clocks only, NO evals
│   ├── jamorgan_blitz_2024h2_analyzed.pgn.gz Aug-Dec 2024 slice, depth-12
│   ├── jamorgan_blitz_2025q1_analyzed.pgn.gz Q1 2025 slice, depth-12 annotated
│   ├── jamorgan_blitz_2025q2_analyzed.pgn.gz Q2 2025 slice, depth-12 annotated
│   ├── jamorgan_blitz_2025q3_analyzed.pgn.gz Q3 2025 slice, depth-12 annotated
│   ├── jamorgan_blitz_2025q4_analyzed.pgn.gz Q4 2025 slice, depth-12 annotated
│   ├── jamorgan_blitz_2023_analyzed.pgn.gz   2023 Lichess, depth-12 annotated
│   ├── jamorgan_blitz_2024rest_analyzed.pgn.gz
│   │                                      2024 Lichess not in the H2 block
│   ├── chesscom_justinmorg_blitz_raw.pgn.gz  all chess.com blitz, unannotated
│   ├── chesscom_justinmorg_2024q4_analyzed.pgn.gz
│   │                                      chess.com Sep-Dec 2024, depth-12
│   ├── chesscom_justinmorg_2026febapr_analyzed.pgn.gz
│   │                                      chess.com Feb-Apr 2026, depth-12
│   ├── chesscom_justinmorg_2023_analyzed.pgn.gz
│   │                                      chess.com Jun-Nov 2023, depth-12
│   └── chesscom_justinmorg_2024janapr_analyzed.pgn.gz
│                                          chess.com Jan-Apr 2024, depth-12
└── scripts/
    ├── annotate.py                           add depth-12 [%eval] to a PGN
    ├── chesscom_filter.py                    raw chess.com export -> blitz PGN
    ├── blockstats.py                         permutation tests across blocks
    ├── annot_inc.py                          resumable annotate — use for big jobs
    ├── longitudinal.py                       compare annotated blocks over time
    ├── outcomes.py                           score from non-winning games; flag wins
    ├── phases.py                              phase map — where losses come from
    ├── material.py                           outcome vs material on board (24..0)
    ├── clockstate.py                         clock state per outcome bucket
    ├── merge.py                              fold new games into the corpus
    ├── hanging.py                            find winning positions where material hung
    ├── features.py                            per-own-move feature tables for all blocks
    ├── multipv.py                             resumable multi-PV — adequate-move counts
    ├── oppmove.py                             opponent's previous move vs my blunder rate
    ├── firstdrop.py                           first major deterioration per game (thread 2)
    ├── forcingtest.py                         missed forcing move, or move that loses to one?
    ├── coincide.py                             do the standing-threat and first-drop findings overlap?
    ├── thread7.py                              does error severity skew fast? (pre-specified; fails)
    ├── clockdecomp.py                          clock effect vs difficulty effect
    ├── ratingexcursion.py                     was a rating peak real, or a random walk?
    ├── quiet43.py                              characterizing the 43% H2 doesn't cover
    ├── pvplayout.py                            delayed tactic or positional decay?
    ├── openings.py                             recover the played book from move times
    ├── build_drills2.py                      rebuild the /chess-drills P set
    ├── build_reflect.py                      rebuild the /chess-drills R (reflection) set
    ├── build_drills.py                       superseded — see below, do not run
    └── test_see.py                            sanity checks for the SEE routine
```

## The corpus

`jamorgan_blitz_2026_analyzed.pgn.gz` is every rated blitz game played by
`jamorgan` in 2026 to date. Verified contents as committed:

| | |
|---|---|
| Games | 1,515 |
| Date range | 2026-01-02 21:52:38 → 2026-08-19 18:48:59 UTC |
| Plies | 98,791 |
| Event type | `rated blitz game` (all 1,515) |
| Results | 721 W / 749 L / 45 D (from the raw `Result` tag, not per-colour) |
| Eval coverage | 98,791 / 98,791 plies |
| Clock coverage | 98,791 / 98,791 plies |
| Duplicate GameIds | 0 |

Every ply carries both an `[%eval]` and a `[%clk]`, in this comment format:

```
{ [%eval 0.38] [%clk 0:03:00] }
```

Mate scores render as `#N` / `#-N` from White's perspective, `#0` for a
delivered mate.

It's stored gzipped to keep the repo small. Decompress before use:

```bash
gunzip -c chess/data/jamorgan_blitz_2026_analyzed.pgn.gz > corpus.pgn
```

### The 2025 file is a different kind of thing

`jamorgan_blitz_2025_raw.pgn.gz` is every rated blitz game from calendar 2025,
pulled 2026-08-24. It is **raw** — clocks on every ply, no evals anywhere — and
the `_raw` suffix is load-bearing. Do not treat it as a second corpus or feed it
to anything that assumes `[%eval]` is present.

| | |
|---|---|
| Games | 2,529 |
| Date range | 2025-01-02 04:12:44 → 2025-12-30 20:06:06 UTC |
| Plies | 169,606 |
| Event type | `rated blitz game` (all 2,529) |
| Results | 1,266 W / 1,161 L / 102 D (raw `Result` tag, not per-colour) |
| Eval coverage | **0 / 169,606 plies** |
| Clock coverage | 169,606 / 169,606 plies |
| Duplicate GameIds | 0 |

It exists because the 2026 corpus alone shows no trend, and the longer view
explains why: mean rating climbed from 1265 (Jan 2025) to 1408 (Jul 2025) and
has been flat in a 1310–1455 band ever since. The plateau is ~13 months old and
started before the 2026 corpus begins. Anything asking "what changed" needs
2025 in frame.

Annotating all 2,529 games is ~170k plies at depth 12 — hours, not minutes.
Prefer annotating a dated slice into its own `_analyzed` file over converting
the whole thing.

**As of Aug 2026 the raw file is fully covered by slices.** Q4 2025 was
annotated last, and the arithmetic closes exactly: 375 (Q1) + 1,559 (Q2) +
363 (Q3) + 232 (Q4) = 2,529. There is no un-annotated remainder in calendar
2025. Keep the raw file anyway — it is the provenance record, and the slices
are derived from it.

### The four annotated slices

`jamorgan_blitz_2025q1_analyzed.pgn.gz` (375 games, 25,610 plies, 2025-01-02 →
2025-03-31) and `jamorgan_blitz_2025q3_analyzed.pgn.gz` (363 games, 25,019
plies, 2025-07-01 → 2025-09-30) are depth-12 annotations of two slices of the
raw 2025 file, committed so the longitudinal comparison below is reproducible
without redoing ~40 minutes of engine work. Full eval and clock coverage, no
duplicate GameIds. Q1 is the pre-climb baseline (mean rating 1317, mean
opponent 1317); Q3 is the plateau onset (1399 / 1396).

`jamorgan_blitz_2025q4_analyzed.pgn.gz` (232 games, 15,006 plies, 2025-10-05 →
2025-12-30) closes the 2025 series. Verified contents as committed:

| | |
|---|---|
| Games | 232 |
| Date range | 2025-10-05 02:45:52 → 2025-12-30 20:06:06 UTC |
| Plies | 15,006 |
| Event type | `rated blitz game` (all 232) |
| Time control | `180+2` (all 232) |
| Results | 119 W / 105 L / 8 D (from the raw `Result` tag, not per-colour) |
| Eval coverage | 15,006 / 15,006 plies |
| Clock coverage | 15,006 / 15,006 plies |
| Duplicate GameIds | 0 |
| Mean rating / opponent | 1377 / 1377 |

The corpus default filter is a **no-op** on this window — every game in
Oct–Dec 2025 is already `rated blitz game` at 180+2, so there are no arena
games, no 5+0 and no 3+0 to drop. Three checks beyond the table: zero GameId
overlap with any other annotated block; ply count and the complete `[%clk]`
series byte-identical to the raw slice, so annotation added evals and touched
nothing else; and the source carried no server evals, so every eval here is
local depth-12 by construction.

It is the smallest block in the corpus (232 games against Q3's 363 and Q2's
1,559) and the thinnest quarter of 2025 — October opens on the 5th, December
stops on the 30th. Treat its intervals accordingly; see "Where Q4 2025 lands"
below for what that does and does not support. No chess.com data was exported
between 2025-01 and 2026-01, so 232 is a lower bound on games actually played
that quarter, not a census.

`jamorgan_blitz_2024h2_analyzed.pgn.gz` (651 games, 42,112 plies, 2024-08-09 →
2024-12-30) is the filtered 2024 block — 3+2 only, non-arena, well clear of the
calibration period (mean rating 1270, mean opponent 1257). It is the earliest
block worth annotating; see the 2023–2024 caveats above for why 2023 was
skipped.

Note its Sept–Dec portion is only 273 games, against 808 played on chess.com
over the same weeks. August is Lichess-heavy (378 games), but from September on
chess.com was the primary site by roughly 3:1. So 2024 H2 is a *sample* of that
period, not a census of it — which is exactly why the chess.com block below is
worth having.

`hanging.py` on the 2026 corpus reproduces 368 hits (290/78) exactly from these
scripts, so all these blocks are directly comparable. That check is the cheapest
tripwire in the repo — run it first in a fresh sandbox, before trusting anything
else a new environment produces.

### What two years actually changed

Reproduce any of this with:

```bash
python3 chess/scripts/longitudinal.py \
  2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn \
  Q4-2025=q4.pgn 2026=corpus.pgn --tc 180+2
```

`longitudinal.py`'s `--tc` takes a **single** value, not the comma-separated
list `outcomes.py`/`features.py` accept. Passing `180+2,300+0` to it matches
nothing and it reports `games=0` for every block — a clean, wrong answer of
exactly the kind this README keeps warning about. The published 2026 figure of
5,517 eligible / 4.33% is the **corpus-default** scope — 3+2 and 5+0, as
`features.py` produces it; 3+2-only gives 2,640 / 4.73%.

**That figure is not what `longitudinal.py` prints with `--tc` omitted.** Aug
2026, chasing what looked like a stale number: dropping `--tc` filters on
nothing at all, so it also admits the 4 games outside the corpus default (3 at
`300+3`, 1 at `180+0`), and returns **5,529 / 4.32%**. The 12-move gap is scope,
not drift. Both numbers are correct for their own scope; quote 5,517 for the
3+2/5+0 default and say which one when quoting the other.

Drop `--tc` to check whether a finding is a time-control artifact — the script
then also prints band 26+ split by `TimeControl`.

Full six-block series, all restricted to **3+2 only**, because the one real
effect lands in the move band where formats diverge. Blunder = own move drops
the eval ≥200cp. Rates per own move:

| move band | 2024 H2 | Q1 2025 | Q2 2025 | Q3 2025 | Q4 2025 | 2026 |
|---|---|---|---|---|---|---|
| 1–12 | 3.58% [3.16, 4.00] | 3.70% [3.15, 4.24] | 3.58% [3.31, 3.85] | 3.53% [3.00, 4.10] | 3.28% [2.62, 3.99] | 3.27% [2.92, 3.63] |
| 13–25 | 10.74% [10.00, 11.46] | 11.43% [10.44, 12.44] | 10.84% [10.37, 11.34] | 11.00% [10.04, 11.99] | 11.45% [10.17, 12.74] | 9.85% [9.19, 10.52] |
| 26+ | 13.15% [12.34, 13.96] | 12.76% [11.78, 13.76] | 12.04% [11.56, 12.52] | 11.52% [10.61, 12.47] | 11.86% [10.56, 13.15] | 9.68% [9.02, 10.34] |

Earlier revisions printed this as a four-block table (2024 H2 / Q1 / Q3 / 2026);
Q2 and Q4 are now filled in. Every point estimate in the old table reproduces
exactly. The interval bounds move by up to 0.03 pp between runs because
`longitudinal.py`'s CIs are unseeded bootstraps — that wobble is the resampler,
not the data.

**Move 26+ is still the only established improvement** — ~26% relative from
2024 H2 to 2026, non-overlapping intervals end to end, against opponents who
got stronger (mean opponent Elo 1257 → 1317 → 1364 → 1396 → 1378 → 1379).

**But it is no longer strictly monotone, and the four-block table overstated
that.** The series runs 13.15 → 12.76 → 12.04 → 11.52 → **11.86** → 9.68: Q4
2025 steps back up above Q3. The two intervals overlap almost completely
([10.61, 12.47] against [10.56, 13.15]) on 4,402 and 2,387 moves, so this is
noise, not a reversal — but it is a reminder that "monotonic across all N
blocks" is a property of which blocks happened to be annotated, and the
moves-13–25 artifact recorded below is the same lesson learned the hard way.
**Quote the endpoint contrast, which is unchanged; do not quote the ordering.**

Moves 13–25 do **not** trend. A three-block read (Q1 2025 / Q3 2025 / 2026)
made this look marginally improving; adding 2024 H2 kills that, since it is
*lower* than Q1 2025. Treat 13–25 as flat. The opening never moved.

Not a format artifact: within 2026, band 26+ is 9.68% in 3+2 vs 10.43% in 5+0,
so the format with *less* clock scores better.

Everything the project actually targets stayed flat. Per eligible winning-
middlegame move (the `hanging.py` denominator: `fullmove > 12`, light npm > 14,
eval ≥ +150). Unlike the blunder table above, these are **pooled across
formats** — the effects sit at median move 20, inside the comparable window:

3+2 only, so it lines up with the blunder table:

| | 2024 H2 | Q1 2025 | Q2 2025 | Q3 2025 | Q4 2025 | 2026 |
|---|---|---|---|---|---|---|
| Eligible moves | 2,090 | 1,224 | 5,005 | 1,300 | 693 | 2,640 |
| Hanging material (0.02 floor) | 5.02% [4.11, 6.03] | 5.23% [4.00, 6.54] | 4.40% [3.84, 4.98] | 4.31% [3.23, 5.46] | 4.33% [2.89, 5.92] | 4.73% [3.94, 5.57] |
| — missed their threat | 4.02% | 4.17% | 3.10% | 3.23% | 2.89% | 3.67% |
| — hung it myself | 1.00% | 1.06% | 1.30% | 1.08% | 1.44% | 1.06% |
| Reached ≥+200 in middlegame | 54.2% | 54.4% | 50.3% | 52.1% | **43.5%** | 53.3% |
| Score from won positions | 62.5% [57.5, 67.1] | 64.3% [57.6, 70.7] | 63.2% [59.8, 66.5] | 63.2% [56.6, 69.8] | 63.9% [54.5, 73.3] | 63.2% [58.5, 67.8] |
| Eval after own move 12 | +81cp | +6cp | −19cp | +9cp | −76cp | −36cp |

All statistically indistinguishable across two years. `hung it myself` is
especially striking — 1.00 / 1.06 / 1.30 / 1.08 / 1.44 / 1.06 across 27 months,
with a six-block label-shuffle at p = 0.86 (see below).

The one cell that looks out of line is Q4 2025's **43.5%** reached. It is
mostly a composition effect and does not survive the control; see "Where Q4
2025 lands" below before quoting it.

The eval@mv12 row has intervals wide enough to be uninformative
(2024 H2 is [−18, +187]); the apparent decline tracks opponent strength rising
by ~120 Elo, not opening skill falling.

The rating climb through mid-2025 tracks the late-game accuracy gain; the
plateau since then tracks a middlegame hanging-material rate that has never
responded to anything. That is the argument for group P being deliberate
practice rather than more games — two years of play did not move it.

That argument got stronger in Aug 2026 in two ways. Q2 2025 was annotated
(1,559 games) and a game-level label-shuffle across all five blocks — 12,259
eligible moves — returned p = 0.71: no block differs from any other. The apparent
Q1→Q3 2025 drop was noise; see "Q2 2025, and why the Q1→Q3 drop was not real".
Second, the same hanging-material rate was measured on 808 concurrent chess.com
games (5.51% vs 5.48% on the date-matched
Lichess games) against opponents 516 Elo lower on the nominal scale. See "The
chess.com corpus" below — the plateau is not an artifact of one site's pool.

Q4 2025 was annotated in Aug 2026, completing the calendar-2025 series and
taking that shuffle to six blocks and 12,952 eligible moves. It returns
**p = 0.86** — the same answer on more data. See "Where Q4 2025 lands".

Caveat on all of the above: score rate sits at ~50% in every block by
construction, since Lichess matchmaking is self-correcting. Rating *level* is
the improvement metric; score rate is not, and neither is anything measured
against opponents whose strength tracks yours.

### Where the other 47% of games go, and how many wins are flags

`outcomes.py` prints the complement of the "score from won positions" row above,
using the same peak definition, so `reached` and `never reached` partition each
block exactly:

```bash
python3 chess/scripts/outcomes.py \
  2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn Q4-2025=q4.pgn \
  2026=corpus.pgn \
  CC-2024Q4=cc_2024q4_analyzed.pgn CC-2026=cc_2026febapr_analyzed.pgn \
  --tc 180+2,300+0 --user-map CC-2024Q4=justinmorg CC-2026=justinmorg

# clock state for the same buckets — takes bare paths, not LABEL=path
python3 chess/scripts/clockstate.py h2.pgn q1.pgn q2.pgn q3.pgn q4.pgn corpus.pgn \
  --tc 180+2,300+0
```

Note `--tc` takes a **comma-separated list**, unlike `longitudinal.py`'s single
value, and `--user-map` sets the player per block so Lichess and chess.com can
go in one call. Scope below is 3+2 and 5+0 across all **eight** annotated
blocks — **5,636 games**, every analyzed game bar seven (4 Lichess at 5+3/3+0,
3 chess.com at 300).

| block | games | reached ≥+200 | score \| reached | score \| never reached |
|---|---|---|---|---|
| 2024 H2 | 651 | 54.2% | 62.5% | 37.1% |
| Q1 2025 | 375 | 54.7% | 64.1% | 34.1% |
| Q2 2025 | 1,559 | 50.3% | 63.2% | 36.4% |
| Q3 2025 | 363 | 52.1% | 63.2% | 36.5% |
| **Q4 2025** | **232** | **43.5%** | **63.9%** | **36.3%** |
| 2026 | 1,511 | 53.9% | 65.6% | 32.0% |
| cc 2024 Q4 | 808 | 55.6% | 63.7% | 34.7% |
| cc 2026 Feb–Apr | 137 | 51.1% | 62.9% | 38.8% |

Pooled: **63.9% [62.2, 65.6]** from 2,966 games that reached a winning position,
**35.0% [33.3, 36.8]** from the 2,670 that never did. Flat across blocks, and
the two chess.com blocks land inside the Lichess spread on both columns —
consistent with the pool-calibration result elsewhere in this README.

Adding Q4 2025 left both pooled figures unchanged to the decimal (63.9% and
35.0%) while adding 232 games. Its two score columns — 63.9% and 36.3% — are
about as close to the pooled values as a 232-game block can land. Its
**reached** column is the exception and is treated separately in "Where Q4 2025
lands" below.

Earlier revisions of this section gave that second figure as both 35.2% and
34.9%. The seven-block measured value was **34.95%** (887.5 points over 2,539
games), recomputed from `features.py`'s `games.csv`; every per-block row in the
table above reproduces exactly, before and after Q4 was added. Use 35.0%.

**Scope warning for everything below this section.** The `outcomes.py` table
above is an eight-block run. The `phases.py`, `material.py`, `features.py`,
think-time, `oppmove.py`, `firstdrop.py` and `forcingtest.py` sections that
follow are all **seven-block runs at 5,404 games and have not been re-run with
Q4 2025 in them.** Their numbers are correct as published for that scope. Do
not mix a figure from one scope into a table built at the other — that is the
same class of error as the 3+2-versus-pooled mismatch documented under
`features.py`.

#### Don't read the 35.0% as a middlegame result

It is a blend of three unrelated things, and 662 of those 2,113 games — 31% —
have **no eligible middlegame moves at all**. Those are not a middlegame state.
They split exactly evenly between two causes, and the two score nothing alike:

- 331 ended by move 13 — score **71.8%**, mostly fast wins
- 331 dropped below light npm > 14 before move 13 — score **47.1%**, early queen
  trades and mass simplification

The quick wins pull the pooled figure *up*. Split the remainder by the
middlegame **trough** — the mirror of peak, same eligibility window:

| middlegame state | games | score | W/D/L |
|---|---|---|---|
| Even (trough > −200) | 442 | 39.8% [35.5, 44.3] | 161/30/251 |
| Losing (−200 to −500) | 400 | 25.4% [21.4, 29.6] | 88/27/285 |
| Lost (≤ −500) | 609 | 10.8% [8.4, 13.4] | 64/4/541 |
| *(no eligible moves)* | *662* | *59.4% [55.8, 63.1]* | *381/25/256* |

Excluding the no-eligible games, the real "played a middlegame and never got on
top" figure is **23.9% [22.0, 25.9]** over 1,735 games, not 35.0%.

**Scope changes between the two tables above, and it is not signposted.** The
block table covers all seven annotated blocks (2,539 never-reached games); this
trough table covers the five **Lichess** blocks only, which is why it sums to
2,113. The 426-game gap is exactly the two chess.com blocks. Verified against
`features.py`: restricting `games.csv` to `site == lichess` reproduces
662 / 442 / 400 / 609 and 59.4 / 39.8 / 25.4 / 10.8% to the digit. Adding
chess.com moves the rows to 804 / 529 / 466 / 740 at 58.8 / 40.5 / 25.4 / 11.0%
— the even-middlegame leak is unchanged, so nothing here turns on it, but quote
the row with its scope attached.

The `lost (≤ −500)` row leans on evals below the depth-12 reliability line; read
it as "clearly lost". The −200 boundary is at the −2 line and is safe.

#### The even-middlegame row is a leak, and it is not a clock leak

**442 games level all the way through the middlegame — never worse than −2,
never better than +2 — score 39.8%.** Against a mean opponent Elo of 1360, with
colour balanced (230 White at 38.9%, 212 Black at 40.8%), that should be nearer
50%. It is stable across blocks: 42.6 / 43.8 / 40.1 / 42.1 / 36.7.

Time is not the explanation. `clockstate.py` on the same buckets, 3+2, median
seconds:

| bucket | mv20 (mine/opp) | mv25 | mv30 | mv40 |
|---|---|---|---|---|
| reached +200 | 104 / 119 (−14) | 72 / 94 (−19) | 46 / 75 (−21) | 26 / 52 (−16) |
| **even** | **115 / 124 (−11)** | **90 / 105 (−14)** | **71 / 89 (−15)** | **45 / 65 (−6)** |
| losing | 101 / 118 (−19) | 74 / 94 (−17) | 48 / 70 (−18) | 25 / 37 (−11) |
| lost | 101 / 121 (−18) | 72 / 94 (−19) | 51 / 70 (−14) | 28 / 46 (−6) |

In even games there is *more* clock left than in any other bucket, the deficit
against the opponent is the *smallest*, and per-move spend is *lower* (7.4s at
moves 16–20 against 8.4s in reached games). Time forfeits are 11.1% of even
games against 13.2% of reached games. The chronic ~15s deficit is a habit
present in every bucket, not something specific to these games.

#### Where they are actually lost: a level endgame

Median length of an even-middlegame game is 37 fullmoves, and 263 of the 442
enter the endgame dead level (median eval at entry −9cp), scoring 43.3%. That
generalises past the never-reached bucket. Over **all** games that reach an
endgame after move 12 (first position with light npm ≤ 14), regardless of
middlegame history:

| eval at endgame entry | all | Lichess | chess.com |
|---|---|---|---|
| winning (> +300) | 1,073 — 79.4% [77.0, 81.6] | 872 — 80.3% | 201 — 75.1% [69.7, 80.6] |
| ahead (+100 to +300) | 401 — **53.2% [48.6, 58.0]** | 334 — 52.2% | 67 — 58.2% [47.0, 69.4] |
| level (−100 to +100) | 774 — **42.7% [39.4, 46.1]** | 641 — 43.1% | 133 — 41.0% [33.1, 49.2] |
| losing (< −100) | 1,443 — 19.1% [17.1, 21.0] | 1,194 — 18.8% | 249 — 20.5% [15.9, 25.5] |

Two rows worth sitting with. A **level** endgame returns 42.7%, with the
interval clearing 50%. And a **one-to-three-pawn advantage** entering an endgame
returns 53.2% — barely better than a coin flip, and the interval covers 50%.

**It replicates across pools.** 650 of the 945 chess.com 3+2 games reach an
endgame, and the level row comes in at 41.0% against 43.1% on Lichess, against
opponents ~500 Elo lower on the nominal scale. Same relationship as the
hanging-material replication in the chess.com section. The `ahead` row is 58.2%
on chess.com against 52.2% on Lichess, but n=67 gives it a 22-point interval —
overlapping, not a difference.

Pooling formats is safe here: split by time control the level row is 42.1%
[38.0, 46.0] at 3+2 (n=529) and 47.8% [38.4, 57.1] at 5+0 (n=112), overlapping
heavily. The 5+0 estimate is too thin to rule out a format effect on its own,
and 42.1% is the conservative figure if one is needed.

This is the strongest direct evidence in the corpus for the endgame track
(groups C/B/A/D), and unlike the hanging-material finding it is not capped:
group P addresses ~24% of blunders in winning positions, whereas these two rows
together are 1,175 games, 22% of everything in scope. Note it does not overlap the
group P denominator — that gate requires eval ≥ +150 *and* npm > 14, so every
game here is outside it by construction.

The `> +300` row sits above the depth-12 reliable band. The other three are
within it.

#### Flag wins

**434 of 2,619 wins — 16.6% — are flags**, and the share is near-identical on
both sites.

`Termination` does not mean the same thing on the two sites, and getting this
wrong is silent. Lichess writes `Time forfeit`; chess.com writes free text —
`"justinmorg won on time"`, `"yossibk5 won on time"`. An equality test against
`Time forfeit` matches **zero** chess.com games and reports a clean, wrong
answer, exactly like the `CHESS_USER` failure documented below. `outcomes.py`
normalises this in `is_flag()` and hard-exits if a run finds no flag wins at
all. chess.com's `"won - game abandoned"` (27 games in the 2024 Q4 block) is a
disconnect, not a flag, and is excluded.

| | games | flag wins | as % of wins | flag losses | as % of games |
|---|---|---|---|---|---|
| 3+2 | 4,661 | 377 | 16.7% | 112 | 2.4% |
| 5+0 | 743 | 57 | 15.5% | 38 | 5.1% |

Flag *wins* are nearly format-independent. Flag *losses* are not — 2.7% vs 5.1%
is the increment doing its job. But do not read that as a clean format contrast:
the 3+2 pool here is overwhelmingly 2024–25 and the 5+0 pool is entirely 2026,
so format and era are confounded. The within-2026 split in the time-control
section above (4.55% vs 4.99%) is the controlled version and shows much less.

Most flag wins were already won. Eval from jamorgan's POV at the moment the
opponent flagged:

| final eval | all flag wins | flag wins in never-reached games |
|---|---|---|
| losing (< −100) | 111 (25.6%) | 63 (39.4%) |
| level (−100 to +100) | 68 (15.7%) | 33 (20.6%) |
| ahead (+100 to +300) | 41 (9.4%) | 13 (8.1%) |
| winning (> +300) | 214 (49.3%) | 51 (31.9%) |
| **total** | **434** | **160** |

So about a quarter of flag wins overall are rescues; half are games where the
clock and the board agreed. Inside the never-reached bucket the composition
inverts — 59% of those 140 came from level or losing positions. That is ~83
games: 12% of the wins in that bucket, and **under 2% of all games in
scope**. Flagging is not propping up the score rate.

Depth-12 caveat applies to the last row of that table only: `> +300` sits above
the reliable band, so read it as "clearly winning" rather than as an exact count.
The +200 threshold defining `reached` is at the +2 line and is safe.

### The phase map: where losses come from, end to end

`outcomes.py` answers "what happened after a winning position." `phases.py`
answers the prior question — *how are games lost at all* — by classifying every
game on three axes and reporting each cell's share of the total loss budget.

```bash
python3 chess/scripts/phases.py \
  2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn 2026=corpus.pgn \
  CC-2024Q4=cc_2024q4_analyzed.pgn CC-2026=cc_2026febapr_analyzed.pgn \
  --tc 180+2,300+0 --user-map CC-2024Q4=justinmorg CC-2026=justinmorg \
  --out /home/claude/phases
```

Entry definitions are imported from `hanging.py`/`outcomes.py`, not restated, so
they agree by construction. Both detections run on **every** ply — see the
endgame-entry ply bug above. The script prints a self-check against the
published endgame-entry table and says `MISMATCH` if it fails to reproduce it;
that check passes on the seven-block run. It also hard-exits on the
`CHESS_USER` silent zero.

Scope below is the standing default: **5,404 games**, seven annotated blocks,
3+2 and 5+0. Record 2,619 W / 200 D / 2,585 L, score **50.3% [49.0, 51.6]** —
which is a matchmaking fact, not a skill measure, per the caveat above.

#### Clock state here is a ratio, and formats are pooled on purpose

This section's clock axis is **own clock against the opponent's in the same
game**, banded at ±10%. That is a deliberate exception to the time-control rule
above. The rule protects against comparing *absolute* late clocks across formats
— 3+2 floors at ~18–20s via the increment, 5+0 has no floor. A ratio never does
that, since it only ever compares two players on the same budget.

Verified before use, not assumed. Score rate by clock state at each entry:

| band | middlegame entry (up/even/down) | endgame entry (up/even/down) |
|---|---|---|
| ±5% | 53.3 / 50.7 / 43.6 | 52.7 / 48.3 / 40.2 |
| **±10%** | **54.1 / 49.6 / 42.7** | **54.1 / 46.4 / 39.8** |
| ±15% | 56.5 / 49.4 / 40.6 | 54.6 / 47.1 / 38.9 |
| ±20% | 59.2 / 49.2 / 37.8 | 56.0 / 46.2 / 38.5 |
| ±25% | 60.2 / 49.2 / 36.3 | 57.6 / 46.0 / 37.6 |

Monotone at every band, and the gap widens as the tails tighten. Split by
format at ±10%, endgame entry: 3+2 gives 53.4 / 45.2 / 39.4% (n = 893/714/1,568)
and 5+0 gives 61.5 / 50.2 / 42.4% (n = 91/207/218) — same ordering, overlapping
intervals, 5+0 a few points higher throughout on a thin sample. Nothing in this
section turns on the choice of band. Use `--clock-band` to re-cut it.

#### 1. Which phase the game ended in

`opening` = no position past move 12; `middlegame` = reached move 13 but never
light npm ≤ 14; `endgame` = an endgame entry occurred.

| phase | games | % games | score | % of all losses |
|---|---|---|---|---|
| opening | 380 | 7.0% | 73.6% | 3.8% |
| middlegame | 1,333 | 24.7% | 57.7% | 21.6% |
| endgame | 3,691 | 68.3% | 45.3% | **74.6%** |

Score falls monotonically with game length. The opening row is favourable
because it is miniatures — a game decided by move 12 usually ended on someone's
blunder and it was more often the opponent's. Do not read 73.6% as opening
strength.

**767 games have no middlegame entry**: 380 ended in the opening and 387 fell
below npm > 14 before move 13 (early queen trades). The latter appear in the
endgame tables with a blank middlegame state; `phases.csv` marks them.

#### 2. State entering the middlegame (n = 4,637)

| eval \ clock | up | even | down | **row** |
|---|---|---|---|---|
| **up** | 419 — 66.6% | 844 — 62.2% | 407 — 56.6% | **1,670 — 61.9%** |
| **even** | 393 — 48.6% | 1,052 — 47.3% | 493 — 38.6% | **1,938 — 45.4%** |
| **down** | 212 — 39.6% | 476 — 32.6% | 341 — 32.0% | **1,029 — 33.8%** |
| **col** | 1,024 — 54.1% | 2,372 — 49.6% | 1,241 — 42.7% | |

**63.0% of all losses started from a middlegame entered level or better**
(1,629 of 2,585). Same conclusion as the opening-is-not-the-problem finding
above, reached as a direct game count rather than from blunder rates.

Eval dominates clock at this point — 28 points across the eval rows against 11
across the clock columns — and the two are close to additive.

#### 3. State entering the endgame (n = 3,691)

| eval \ clock | up | even | down | **row** |
|---|---|---|---|---|
| **up** | 432 — 76.5% | 361 — 72.7% | 681 — 69.3% | **1,474 — 72.3%** |
| **even** | 203 — 50.0% | 246 — 41.1% | 325 — 39.4% | **774 — 42.7%** |
| **down** | 349 — 28.8% | 314 — 20.2% | 780 — 14.2% | **1,443 — 19.1%** |
| **col** | 984 — 54.1% | 921 — 46.4% | 1,786 — 39.8% | |

The eval rows are the published endgame-entry table with `>+300` and
`+100..+300` merged (1,073 at 79.4% + 401 at 53.2% = 1,474 at 72.3%). Nothing
new. The clock axis is the new information.

**30.5% of all losses are endgames entered level or better** (789 games); 14.3%
are endgames entered *ahead* (370). That is the endgame-technique case restated
as a loss budget rather than a score rate.

**A clock deficit is a conditional tax, not a flat one.** The up→down clock
spread inside each eval row: 7 points when winning (76.5 → 69.3), 11 when level
(50.0 → 39.4), 15 when losing (28.8 → 14.2). It costs little when the position
is already won and roughly halves the recovery rate when it is not. The single
largest cell in the loss budget is losing-eval-plus-losing-clock: 780 games,
14.2%, **25.4% of all losses**.

**It is not a flag artifact.** Flags are 5.8% of all losses (150 of 2,585), and
9.0% even within the clock-down endgame column. Over 90% of those games were
lost on the board. Consistent with the think-time result that clock pressure is
the smaller of the two effects.

#### 4. How the eval travels, middlegame entry → endgame entry

Games reaching both, n = 3,304. Cell: games, score, share of all losses.

| mg ↓ / eg → | up | even | down |
|---|---|---|---|
| **up** | 751 — 74.3% — L 6.8% | 161 — 40.7% — L 3.5% | 266 — 14.5% — L 8.7% |
| **even** | 446 — 70.6% — L 4.5% | 375 — 42.0% — L 7.9% | 604 — 20.1% — L **18.2%** |
| **down** | 140 — 75.7% — L 1.2% | 80 — 50.0% — L 1.4% | 481 — 18.8% — L 14.7% |

**The largest single flow in the corpus is level middlegame → losing endgame:
604 games, 471 losses, 18.2% of all losses.** The advantage-thrown-away path
(up → down) is 266 games and 8.7% — real, but less than half as large. That is
independent confirmation of the ~24% ceiling on group P from a different
direction: the corpus does not mostly lose won games, it mostly loses level
ones.

The middlegame leaks both ways — 446 games went level → winning and 140 losing →
winning — and only 375 of the 1,025 that entered level were still level at the
endgame. The diagonal is not stable in either direction.

#### 5. The permutation table is flat

98 occupied (phase × mg state × eg state) cells. Top 20 hold 59.3% of losses,
no single cell exceeds 5.8%, median occupied cell ~12 losses. **The marginals
carry the signal; the joint cells are too thin to interpret.** The two largest
are the same story — entered the middlegame level, entered the endgame losing
and short of time — together 331 games, 274 losses, 10.6% of all losses.

`permutations.csv` and the per-game `phases.csv` regenerate in ~90 s and are
gitignored, same policy as the `features.py` tables. Commit the script, not the
output.

#### What it does not settle

Clock state at endgame entry is measured *after* the middlegame that produced
it, so "short of time" and "had a hard middlegame" are substantially the same
event. This design cannot separate them, and the think-time section's warning
applies unchanged: **nothing here licenses moving faster.** Whether the clock
effect survives conditioning on position difficulty is untested and would need
the same direct-standardization treatment used there. Whether the level→losing
flow is a technique, time or judgment failure is open thread 2, which needs no
new data.

### Outcome vs material on the board, and the benchmark trap

`material.py` cuts the corpus on a third axis: `npm(board, "light")` — N=1, B=1,
R=2, Q=4, both sides — which runs from **24 at the starting position to 0 at
bare kings**, the same scale the endgame threshold (≤ 14) is defined on. For
each game and each level M it takes the first position where npm ≤ M and asks
how the game ended.

```bash
python3 chess/scripts/material.py \
  2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn 2026=corpus.pgn \
  CC-2024Q4=cc_2024q4_analyzed.pgn CC-2026=cc_2026febapr_analyzed.pgn \
  --tc 180+2,300+0 --user-map CC-2024Q4=justinmorg CC-2026=justinmorg \
  --out /home/claude/mat
```

**Correctness anchor:** M=24 is the starting position of every game at eval 0,
so that row must hold all 5,404 games at exactly the corpus score rate. It does.
If the left edge is anything else the pass is broken, and the script says so.

#### The benchmark is not 50%. This is the whole point of the section.

The first version of this analysis compared level-position score against 50% and
reported a flat 7-point deficit at every material level. **That was wrong, and
the error is instructive enough to keep on the record.**

A level position scores 50% only within a *symmetrically selected* population,
and "reached npm M" is not one. The phase map already established that wins end
early and losses run long — opening 73.6%, middlegame 57.7%, endgame 45.3% — so
conditioning on reaching low material selects a population scoring well below
50% before the eval is mentioned at all. The correct benchmark is the score of
**every** game reaching the same level, and the finding is the difference.

| npm | reach | benchmark | level n | level | **diff** |
|---|---|---|---|---|---|
| 24 | 5,404 | 50.3% | 5,404 | 50.3% | +0.0 |
| 22 | 5,242 | 49.5% | 3,011 | 47.8% | −1.7 |
| 20 | 4,999 | 48.4% | 1,947 | 46.0% | −2.4 |
| 19 | 4,790 | 47.8% | 1,330 | 43.5% | **−4.3** |
| 18 | 4,620 | 47.8% | 1,326 | 44.1% | **−3.7** |
| 17 | 4,394 | 47.1% | 942 | 43.9% | −3.1 |
| 16 | 4,219 | 46.9% | 940 | 43.1% | **−3.8** |
| 15 | 4,011 | 46.2% | 791 | 42.9% | −3.4 |
| 14 | 3,858 | 46.0% | 800 | 43.1% | −2.9 |
| 13 | 3,663 | 45.3% | 686 | 42.8% | −2.5 |
| 12 | 3,477 | 45.1% | 692 | 43.0% | −2.1 |
| 11 | 3,280 | 44.8% | 563 | 44.7% | **−0.1** |
| 10 | 3,110 | 44.6% | 560 | 44.2% | **−0.4** |
| 9 | 2,863 | 44.2% | 442 | 42.9% | −1.3 |
| 8 | 2,655 | 44.3% | 438 | 42.4% | −1.9 |
| 7 | 2,393 | 44.1% | 334 | 47.0% | +2.9 |
| 6 | 2,167 | 43.2% | 334 | 45.1% | +1.9 |
| 5 | 1,849 | 42.7% | 259 | 41.7% | −1.0 |
| 4 | 1,571 | 42.4% | 287 | 41.8% | −0.6 |
| 3 | 1,180 | 41.6% | 147 | 40.8% | −0.8 |
| 2 | 965 | 41.9% | 134 | 40.3% | −1.6 |
| 1 | 650 | 39.4% | 104 | 41.8% | +2.4 |
| 0 | 418 | 38.3% | 76 | 46.7% | +8.4 |

The level column is flat at ~43% because two things move oppositely: the
benchmark falls steadily as material comes off, while the level score does not.
Against 50% that reads as a uniform 7-point deficit at every level. Against the
right benchmark it reads as **a 3–4 point deficit concentrated at npm 19–13 that
closes to zero from npm 11 down.**

#### What this changes

1. **The level-position deficit is a middlegame effect.** Largest at npm 19, 18,
   16 (−4.3, −3.7, −3.8); indistinguishable from zero at npm 11 and 10 (−0.1,
   −0.4). From equality, you fall behind comparable games early and then hold par
   for the rest of the game.

2. **The published 42.7% at endgame entry is not a special endgame number, but
   not for the reason first proposed.** It is the same absolute ~43% seen at npm
   18 and 16 — however at endgame entry that is roughly *par* for the material
   level, while at npm 18 the identical 43% is nearly 4 points *below* par. The
   endgame-entry level bucket looks bad mostly because every game still alive at
   that point looks bad.

3. **The dominant effect on this axis is game length, not eval.** The benchmark
   column falls monotonically 50.3% → 38.3%. That is the phase map's
   win-fast-lose-slow finding restated on the material axis, and it is larger
   than anything the eval conditioning produces.

4. **This is a point against prioritising endgame technique** (groups C/B/A/D),
   by a different argument than the one first given: from npm 11 down you already
   score at par for the material on the board.

#### The other half: what keeps the total at 50%

The level column is only a third of each row. `material.py` also prints the
`ahead` and `behind` columns, and they are where the compensation lives:

| npm | ahead n | ahead score | behind n | behind score |
|---|---|---|---|---|
| 23 | 1,406 | 62.6% | 767 | 34.6% |
| 19 | 1,918 | 68.6% | 1,542 | 25.7% |
| 16 | 1,719 | 72.3% | 1,560 | 21.2% |
| 12 | 1,379 | 74.5% | 1,406 | 17.2% |
| 8 | 1,046 | 78.4% | 1,171 | 14.5% |
| 4 | 556 | 82.1% | 728 | 12.3% |
| 2 | 357 | 86.3% | 474 | 9.0% |

Two things move monotonically as material comes off. **Conversion from ahead
climbs from 62.6% to 86.3%** — simplification does what it should when you are
the one with the edge. **Recovery from behind collapses from 34.6% to 9.0%** —
once you are worse, every trade closes a door.

You are also ahead more often than behind at most levels (1,918 vs 1,542 at npm
19). So the corpus-wide 50.3% is not "average player": it is an above-par rate
of acquiring advantages, decent conversion, and a small deficit from equality,
netting out. The `behind` collapse is the strongest case in this table for
endgame study, but note it is about *holding worse positions*, which is a
different skill from the level-endgame technique in open thread 3.

#### The clock cut

Level positions split by clock state (ratio, ±10%, the `phases.py` cut) at the
first level crossing in npm 19–4, one observation per game:

| clock | all games | all score | level n | level score |
|---|---|---|---|---|
| up | 1,211 | 56.8% | 337 | **51.6%** |
| even | 1,811 | 48.7% | 581 | **43.7%** |
| down | 1,768 | 40.9% | 412 | **36.7%** |

A 15-point spread, stable at every material level from 23 down to 5 (clock-up
level positions sit at 50–56% throughout, clock-down at 36–42%) — the script
prints that per-level breakdown so the stability claim is checkable rather than
asserted. Exposure is
lopsided: clock-down at 36.9% of crossings against clock-up at 25.3%, the
chronic deficit showing up as a volume problem.

**But the clock does not explain the deficit away.** Tightening both bands
together, the symmetric cell — level eval *and* level clock — does not close:

| eval band | clock band | n | score |
|---|---|---|---|
| ±100 | ±10% | 581 | 43.7% |
| ±50 | ±10% | 357 | 41.3% |
| ±50 | ±5% | 211 | 41.5% |
| ±25 | ±5% | 118 | 40.3% |
| ±10 | ±10% | 105 | 39.0% |

Mean clock ratio inside the "even" band is 0.9948 — half a percent, nowhere near
enough to manufacture a gap. From a dead-level position with a dead-level clock
the score is still ~41–43%. The clock reallocates the deficit rather than
accounting for it.

**Causal caution, unchanged and now more load-bearing.** Clock state at a
material crossing is downstream of the middlegame that produced it; a long think
means a hard position. The 15-point spread is equally compatible with "clock
deficits cost games" and "hard positions cost both time and games," and this
design cannot separate them. The multi-PV work already found the difficulty
interaction did not replicate. Nothing here licenses moving faster.

#### Reading the table honestly

* **~12 independent points, not 25.** Material falls in jumps, so one position is
  the first crossing for several adjacent M. Odd levels are mid-exchange, the
  even level below is the completed trade; the pairing is visible throughout
  (23/22 → 3,129 and 3,011 games at 48.0/47.8%; 21/20 → 45.7/46.0%). Local
  wiggles are noise.
* **Survivorship.** Only 29.1% of games are still present at npm 4. Different M
  are different populations, not the same games followed down.
* **Depth-12 at low material.** The ±100 band is inside the reliable range for
  middlegames, but depth 12 is genuinely weak in endgames, where a position it
  calls 0.00 can be theoretically won or lost. The npm ≤ 4 rows are the softest
  in the table for that reason on top of their sample size — the +8.4 at npm 0
  on 76 games is not a finding.
* Replication of the absolute level curve: lichess (4,459 games) and chess.com
  (945) agree within a point or two at every level; six of seven blocks fall
  between 40.8% and 46.4%. Holds at bands from ±200 down to ±10cp.
* Symmetry checks run before believing the deficit, all passed: side-to-move at
  the crossing (42–48% either way), colour (White 42.1%, Black 45.8% pooled over
  npm 20–4), mean eval inside the ±100 band (slightly *positive*, +12cp at npm
  22 falling to ~0, so it would push score up not down), and eval annotation
  coverage (100% of plies, so the eval at each crossing is that position's own
  and never stale). None of these is large enough to manufacture the effect —
  which is why the benchmark, not a measurement artifact, turned out to be the
  problem.

### Q2 2025, and why the Q1→Q3 drop was not real

Q1 2025 (5.23%) and Q3 2025 (4.31%) were annotated before Q2, and the apparent
drop between them was the only movement in the hanging-material table. It looked
like something had changed mid-2025, right where the rating plateau begins.
Q2 was annotated (1,559 games — larger than Q1 and Q3 combined) to find out
whether the change was gradual or stepped.

It was neither. Monthly, per eligible winning-middlegame move, floored:

| month | games | eligible | floored rate |
|---|---|---|---|
| Apr 2025 | 407 | 1,340 | 4.85% |
| May 2025 | 477 | 1,653 | 4.96% |
| Jun 2025 | 675 | 2,012 | 3.63% |
| **Q2 total** | **1,559** | **5,005** | **4.40% [3.84, 4.96]** |

June looks like a sharp dip. It is not one. Testing it requires correcting for
the fact that June was chosen *because* it was the lowest of three months, so
the test shuffles game-to-month labels and asks how often the **minimum** monthly
rate falls that low by chance: p = 0.13. The spread across the three months
gives p = 0.20. Both null.

**With Q2 in place, the flatness result is much stronger than before.** Five
blocks, 12,259 eligible moves:

| block | eligible | floored rate | hung it myself |
|---|---|---|---|
| 2024 H2 | 2,090 | 5.02% | 1.00% |
| Q1 2025 | 1,224 | 5.23% | 1.06% |
| Q2 2025 | 5,005 | 4.40% | 1.30% |
| Q3 2025 | 1,300 | 4.31% | 1.08% |
| Q4 2025 | 693 | 4.33% | 1.44% |
| 2026 | 2,640 | 4.73% | 1.06% |

Game-level label-shuffle, 20,000 shuffles, seed 23. Five blocks when this was
first run, six now that Q4 2025 is in (12,952 eligible moves):

| | five blocks | six blocks (with Q4) |
|---|---|---|
| hanging material | spread 0.92 pp, **p = 0.71** | spread 0.92 pp, **p = 0.86** |
| hung it myself | spread 0.29 pp, **p = 0.91** | spread 0.44 pp, **p = 0.86** |

No block differs from any other on either measure, before or after Q4. The
Q1→Q3 drop was sampling noise in two small blocks, and Q2's tight interval
anchors the middle of the series. Do not re-chase it — same category as the
moves-13–25 block-selection artifact recorded above.

Adding Q4 does not move the hanging-material spread at all: at 4.33% it lands
between Q3 (4.31%) and 2026 (4.73%), so the min and max blocks are unchanged
and Q4 is not even the extreme. Its `hung it myself` of 1.44% is the highest
of the six, which is precisely the shape of the flag Q2 raised and lost — 10
floored hits on 693 eligible moves, at p = 0.86. Not a finding; do not raise
it as one a third time.

This also **retracts a flag raised when Q2 was first measured**: Q2's `hung it
myself` rate of 1.30% looked elevated against the 1.00/1.06/1.08/1.06 of the
other blocks, and within Q2 it declined monthly (1.79 → 1.39 → 0.89). At p =
0.91 across blocks, none of that is real. Two large blocks landing high is what
noise looks like when most blocks are small.

### Where Q4 2025 lands

Q4 2025 (232 games, Oct–Dec) was annotated in Aug 2026 to close the 2025
series. It is the **smallest block in the corpus** and the thinnest quarter of
2025, so the prior expectation was wide intervals and no resolving power. That
is broadly what happened.

**On everything the project actually targets, Q4 changed nothing.**

| | Q4 2025 | six-block range | test |
|---|---|---|---|
| hanging material (floored) | 4.33% [2.89, 5.92] | 4.31 – 5.23% | spread p = 0.86 |
| — hung it myself | 1.44% [0.58, 2.45] | 1.00 – 1.44% | spread p = 0.86 |
| blunder 1–12 | 3.28% | 3.27 – 3.70% | — |
| blunder 13–25 | 11.45% | 9.85 – 11.45% | — |
| blunder 26+ | 11.86% | 9.68 – 13.15% | — |
| score from won positions | 63.9% | 62.5 – 65.6% | — |

Its hanging-material rate lands *between* Q3 and 2026, so the min and max
blocks are unchanged and the observed spread is identical at 0.92 pp — adding
a whole quarter of play moved the homogeneity result from p = 0.71 to p = 0.86
and nothing else. Its conversion rate of 63.9% is the pooled corpus figure to
the decimal. The pooled `outcomes.py` rows (63.9% / 35.0%) are unchanged with
232 more games in them.

Two things it did change, both small and both worth stating plainly:

- It puts a **non-monotone step in the move-26+ series** (Q3 11.52% → Q4
  11.86% → 2026 9.68%). The intervals overlap almost entirely; the endpoint
  contrast that carries the finding is untouched. See the blunder table above.
- Its **`hung it myself` of 1.44% is the highest of the six Lichess blocks.**
  This is the third time a newly annotated block has come in high on that
  measure, and the previous two were both retracted. Ten floored hits on 693
  eligible moves, p = 0.86. It is noise.

#### The one apparent difference, and why it is not a finding

Q4's **reached ≥+200 rate is 43.5%**, against 50.3–55.6% in every other block —
the only cell in any table where Q4 is visibly out of line. Tested the same way
`blockstats.py shuffle` works (game-level label shuffle, 20,000 draws, seed 23),
computed from `features.py`'s `games.csv`, since `blockstats.py` implements only
`hang` and `hungself` — same situation as the rarefaction tests in the
chess.com section, which it also does not implement.

Q4 was singled out **because** it looked extreme, so the minimum-block p is the
one that applies to it; the spread p is reported alongside for the "does any
block differ" question:

| metric | Q4 | others | spread p | Q4-block p |
|---|---|---|---|---|
| reached, **raw** | 43.5% | 50.3 – 55.6% | 0.020 | **0.0045** |
| games with **no eligible middlegame** | 21.6% | 12.5 – 16.1% | 0.0075 | **0.0057** (max) |
| reached, **games that had a middlegame** | 55.5% | 59.2 – 65.3% | 0.14 | **0.059** |

*(six Lichess blocks; over all eight the same three rows give 0.061 / 0.018,
0.045 / 0.026, and 0.24 / 0.12 — every one of them weaker.)*

**The raw difference is mostly composition, not conversion.** A game with no
eligible middlegame move cannot reach +200 by construction — the same
definitional trap the `material.py` benchmark section and the
`opp_created_threat` row both record. Q4 has 21.6% such games against 12.5–16.1%
elsewhere, and that gap is where the signal sits. Condition on games that
actually had a middlegame and Q4 rises from 43.5% to 55.5%, the spread test goes
null (p = 0.14), and the block-level p degrades to 0.059. The composition
difference is specifically the **early-simplification** cause, not the
short-game one: 13.4% of Q4 games drop below light npm > 14 before move 13
against 6.4–9.1% elsewhere, while games ending by move 13 are 8.2% against
6.1–7.7% — in line.

**This is not a finding, and it should not be written up as one.** Four reasons,
in descending order of how much they should bother you:

1. **It is post-hoc down two levels.** The reach% cell was spotted by eye, then
   decomposed into composition, then into a cause. Each level multiplies the
   forking paths, and none of it was pre-specified.
2. **Roughly ten metrics were examined** across `longitudinal.py`,
   `outcomes.py` and the shuffles before this one stood out. A nominal p =
   0.0057 does not survive that honestly.
3. **The controlled version is null.** The thing anyone would care about —
   whether he converted fewer games into winning positions — comes back at
   p = 0.059 / 0.12 once the mechanical part is removed.
4. **232 games, and no replication anywhere.** This is the smallest block in
   the corpus. The corpus already has three retracted findings and every one of
   them was a suggestive pattern in a small block with a plausible mechanism
   attached.

What is mildly reassuring against a one-session artifact: the elevated
no-eligible share is stable across all three months (23.8 / 20.7 / 20.8%), not
a single burst. What that does *not* do is make it replicate.

**Status: an untested flag, deliberately not added to the do-not-re-chase list
below.** That list is for hypotheses that were chased and lost. This one has
not been tested against anything independent, and the honest position is that
nobody knows. If it ever matters, the cheap version is to check opening and
early-queen-trade composition in Q4 against the adjacent quarters *from the raw
2025 file*, which needs no new engine time. **`blockstats.py` now implements
`reached`, `noelig` and `reached_mg` as game-level metrics, so the table above
is reproducible from committed tooling rather than from an ad-hoc groupby:**

```bash
python3 chess/scripts/blockstats.py shuffle \
    2024H2=h2.pgn Q1=q1.pgn Q2=q2.pgn Q3=q3.pgn Q4=q4.pgn 2026=corpus.pgn \
    --tc 180+2,300+0 --metric reached --seed 23
```

Every rate reproduces to the decimal — Q4 43.53 / 21.55 / 55.49% against the
43.5 / 21.6 / 55.5% published above, and each of the five other blocks lands on
its published value. The p-values agree to within Monte Carlo noise (0.0196
against 0.020 on the spread, 0.0050 against 0.0045 on the Q4 block, 0.0072
against 0.0075, 0.1317 against 0.14, 0.0646 against 0.059); the original run
used a different RNG stream, and none of the differences changes a conclusion.
**The controlled row stays null**, which was the thing worth confirming.

Three things changed in `blockstats.py` to make this work, all documented in
its docstring:

1. **The game metrics divide by games, not by eligible moves**, and they mirror
   `outcomes.py`'s eligibility, which has **no `cp >= 150` gate** — unlike
   `blockstats.py`'s existing `eligible` counter, which does. Reusing that
   counter would have silently redefined the metric. The two are tracked
   separately in `per_game`. Never compare a rate from one family against a
   rate from the other; the denominators are different things.
2. **`--tc` now takes a comma-separated list**, because the published Q4 table
   is a `180+2,300+0` run and the old single-value argument could not express
   it. A single value still works. `cmd_clock` stays single-tc on purpose — it
   reads the increment out of the string.
3. **`shuffle` now also prints a maximum-block p.** The `noelig` row needed it:
   Q4 is the *highest* block there, and only the minimum-block p was being
   computed, so the row could not be tested at the end it was extreme at.

**And one bug found while doing it, worth recording on its own.**
`blockstats.py`'s `CHESS_USER` guard was **dead**. It read
`if rows and not stats["matched"] and stats["games"]`, but nothing in
`per_game` ever incremented either counter — they were only touched inside
`probe()`, which populates a different dict. The guard could never fire, so
the one silent-zero this README warns about most had an inert tripwire sitting
in front of it. It now counts locally and hard-exits properly. This mattered
immediately: the game metrics run with `need_hits=False` and skip `probe()`
altogether, so the old guard would have been doubly dead on exactly the new
code path.

That is the same class of failure as everything else in this file's guardrails
list — no error, plausible output, and the only way to catch it is to check
that a known number reproduces.

Do not act on it, do not build a mechanism story around it, and do not let it
into a summary as "Q4 2025 converted fewer games."

### The Jan/Feb 2026 rating peak was a random walk

Aug 2026. On **2026-02-06 the rating hit 1508**, the all-time Lichess blitz high
across all 5,686 games in the corpus (previous best 1457, 2025-07-15; the
2023–24 file tops out at 1371). It arrived after a visible run of wins in late
January. The question this section settles: was that a genuine short spell of
better play, or the excursion a constant-strength player's rating takes anyway?

**It was the excursion. Nothing about the play changed.**

Script: `ratingexcursion.py`, written to be reusable for the next excursion —
trigger 2 under "When it is worth pulling a fresh batch" exists to flag these,
and this is what adjudicates one without annotating a new block.

```bash
python3 chess/scripts/ratingexcursion.py corpus.pgn \
    --window 2026-01-20:2026-02-14 --window 2026-02-04:2026-02-14 \
    --tc 180+2 --until 2026-04-30 --seed 23
```

Pool is 2026 at **3+2 only, through 2026-04-30** — 573 games. Cut there because
the format switches to 5+0 in May (see "Time control changed mid-2026"), and a
format change inside the baseline would confound the contrast.

#### Why the obvious test is the wrong test

**The window is selected because the results were good.** Nearly every
move-quality measure correlates with winning, so under a null of constant skill
the best-results window *still* shows better-looking quality. A plain
window-vs-rest permutation is biased toward finding improvement and cannot
answer the question. This is the same class of error as the June 2025 dip —
a bucket singled out for being extreme, then tested as though it hadn't been.

The headline test (T2) puts the selection **inside the null**: each shuffle
re-runs the same cherry-pick — find the hottest 186-game window in the shuffled
order — and measures *that* window's quality. The observed window is then
compared against windows selected the same way by luck alone. The naive test is
still printed as T3, labelled biased, so the size of the bias stays visible.

#### Pre-specified before any output was inspected

- Primary window **W1 = 2026-01-20 → 2026-02-14** (186 games), Justin's own
  description of the run. Sensitivity **W2 = 2026-02-04 → 2026-02-14** (63
  games), the excursion already tabulated under "Checking the rating trigger by
  eye".
- Primary quality metric: mean win probability lost per own move. Secondary:
  blunder rate moves 13+, blunder rate all moves, floored hanging material.
- **Decision rule: conclude "genuinely better" only if the primary metric is
  better at p < 0.05 under T2.** T3 alone is not sufficient and will not be
  quoted as evidence.

#### Results

Descriptives, W1 against the rest of the pool:

| | W1 (Jan 20 – Feb 14) | rest of Jan–Apr 3+2 | whole pool |
|---|---|---|---|
| games | 186 | 387 | 573 |
| score | 0.527 | 0.475 | 0.492 |
| mean opponent Elo | 1450 | 1370 | 1396 |
| win prob lost per own move | 0.0387 | 0.0395 | 0.0392 |
| blunder rate, moves 13+ | 9.07% | 9.72% | 9.50% |
| hanging material (floored) | 4.39% (661 elig) | 4.92% (1,381 elig) | 4.75% |

Every quality metric leans *better* in W1, and not one of them is close to
significant:

| metric | W1 | null mean | **p (T2)** | p (T3, biased) | detectable at 80% |
|---|---|---|---|---|---|
| win prob lost / move | 0.0387 | 0.0385 | **0.554** | 0.609 | 0.0028 |
| blunder rate 13+ | 9.07% | 9.26% | **0.338** | 0.331 | 1.21 pp |
| blunder rate, all | 6.85% | 7.08% | **0.214** | 0.173 | 0.81 pp |
| hanging material | 4.39% | 4.58% | **0.399** | 0.624 | 1.97 pp |

20,000 shuffles for T1, 5,000 for T2/T3, seed 23, game-level resampling.

**T1 — was the streak itself extreme?** The best 186-game stretch in the real
data scores 0.573 (2026-01-02 → 02-07). Shuffling the pool, the best window
averages 0.545 and reaches 0.578 in 5% of shuffles: **p = 0.082**. The longest
win streak, 10 games (2026-01-19 → 01-25), comes up at **p = 0.166**. Neither
is unusual for 573 games. Window-length sensitivity (k = 30/48/63/100/150/186)
gives p between 0.08 and 0.36 with no consistent pattern — the signature of
noise, not of a real hot spell.

**Elo over/under-performance.** W1 scored 52.7% against an Elo-expectation of
49.2% — **+3.4 pp, exactly 1.0 standard error**. W2 is +1.2 pp (0.2 SE). The
rest of Jan–Apr runs −2.2 pp. Net rating is **+78 in W1 and −84 over the rest**,
round-tripping to −6 across four months. Same play, rating oscillating around
it. Mean opponent Elo rising 1370 → 1450 inside the window is matchmaking
following the rating, and is what pulls it back.

#### Resolution — what this could and could not have caught

The accuracy test would have caught an improvement of **0.0028 win probability
per own move, about 3 centipawns per move near a level position** — roughly a
7% relative improvement in average move quality. Observed gap is 0.0008, about
a quarter of that. The blunder test would have caught 9.07% → 7.9%. The hanging
test is the weak one: at 661 eligible moves it could only have caught a change
of ~2 pp, i.e. 4.4% → 2.4%, so a moderate real improvement in *that* metric
would have been invisible. "No improvement" here means no improvement large
enough to matter, not proof of identity.

#### What this is good for

It converts an assumption into a measurement. The 2026-02-04 → 02-14 excursion
was already in the trigger-2 calibration table as the largest of 33 excursions
across a known-flat 13-month plateau, i.e. *assumed* to be noise because the
surrounding period was flat. It has now been tested directly and is noise.

It is also the cleanest available calibration for how loud the noise is:
**~150 rating points of movement with no detectable change in play at all.**
Quote that before reading anything into a rating swing.

No study-plan consequence. There is no February technique to recover, and group
P remains the priority.

### Complete 3+2 / 5+0 coverage, and what the beginner era shows

Aug 2026: every remaining game at **3+2 or 5+0** on both sites was annotated at
depth 12, closing the corpus for those two formats. 1,683 games / 101,171 plies,
~70 minutes single-core.

**The scope decision, stated so it is not re-litigated.** Only 3+2 and 5+0 are
in scope. Arena games are out (4 Lichess `≤1700 Blitz Arena`). Every other time
control is out and stays out: **3+0** (1,072 chess.com, 151 Lichess), **5+3**
(108 Lichess) and 300+2 (2 chess.com). 3+0 in particular is a harsher clock
regime that this project has never verified as poolable, so it would need its
own comparison rather than a row in an existing table.

**Calibration-period games are included this time**, unlike the earlier
treatment which dropped the account's first ~60 games while Lichess converged
from its 1500 default. Keeping them makes the corpus complete and turns the
exclusion into an analysis-time choice — filter on date if you want them out.
Be aware they are in there: the 2023 Lichess block opens at 2023-03-22.

| block | games | plies | window | formats | mean Elo (self/opp) |
|---|---|---|---|---|---|
| `jamorgan_blitz_2023` | 596 | 34,908 | 2023-03-22 → 2023-10-29 | 587 3+2, 9 5+0 | 926 / 931 |
| `jamorgan_blitz_2024rest` | 132 | 8,373 | 2024-01-09 → 2024-12-27 | 9 3+2, 123 5+0 | 1176 / 1178 |
| `chesscom_justinmorg_2023` | 359 | 21,143 | 2023-06-14 → 2023-11-17 | 351 3+2, 8 5+0 | 646 / 645 |
| `chesscom_justinmorg_2024janapr` | 596 | 36,747 | 2024-01-01 → 2024-04-04 | 71 3+2, 525 5+0 | 670 / 675 |

Records: 290W/269L/37D, 69W/55L/8D, 164W/183L/12D, 298W/287L/11D. All four
verified the same way as every other block — full eval and clock coverage on
every ply, ply count and the complete `[%clk]` series byte-identical to the
source slice, GameId set equal to source, zero duplicates, uniform `Event`, no
malformed eval tokens, and no server evals anywhere in the sources.

`jamorgan_blitz_2024rest` is the odd one and needs its name explained: it is the
2024 Lichess games at 3+2/5+0 that the **3+2-only** 2024 H2 block does not
carry. It is mostly 5+0, and only 4 of its games fall inside H2's Aug 9 – Dec 30
window. It is not a second sample of the same period.

#### The positive control: this metric does move

The corpus's central claim is that hanging material never responded to anything
over two years. The obvious objection is that the measure might simply be
incapable of moving — flat by construction rather than flat as a finding. The
beginner-era blocks answer that, and they are the first thing in this project
that makes the flatness result falsifiable rather than merely repeated.

Lichess, 3+2, floored hanging material per eligible winning-middlegame move:

| block | eligible | hanging | hung it myself | mean opp Elo |
|---|---|---|---|---|
| **2023** | 1,793 | **7.98% [6.75, 9.26]** | **2.68%** | 929 |
| 2024 H2 | 2,090 | 5.02% | 1.00% | 1257 |
| Q1 2025 | 1,224 | 5.23% | 1.06% | 1317 |
| Q2 2025 | 5,005 | 4.40% | 1.30% | 1364 |
| Q3 2025 | 1,300 | 4.31% | 1.08% | 1396 |
| Q4 2025 | 693 | 4.33% | 1.44% | 1378 |
| 2026 | 2,640 | 4.73% | 1.06% | 1379 |

Game-level label-shuffle, 20,000 draws, seed 23:

- six settled blocks (2024 H2 onward): spread 0.92 pp, **p = 0.86**
- **add 2023: spread 3.67 pp, p = 0.0030**
- `hung it myself`, same two runs: **p = 0.86** → **p = 0.0066**

So the instrument detects a ~450-Elo difference in skill at p = 0.003 on the
same test that returns 0.86 across the whole settled era. **The flatness result
is a real null, not an insensitive measure.** That is the entire value of these
blocks and it is worth more than the extra sample size.

What it is **not**: evidence that anything he did moved the rate. This contrast
is a 900-Elo player against a 1370-Elo player, which is a statement about the
gap between beginner and settled play, not about training. Nobody should read
"the rate fell from 7.98% to 4.5%" as an achievement to repeat — the rating
climb over that span is the thing being described, and this is one more view of
it.

The chess.com series leans the same way and **does not reach significance on its
own**: 7.65% (2023) / 7.09% (2024 Jan–Apr) / 5.51% (2024 Q4) / 4.95% (2026),
spread p = 0.38, `hungself` p = 0.11. The two early blocks are 351 and 71 games
at 3+2, so this is underpowered rather than contradictory. Do not describe the
positive control as "replicating across pools" — one site carries it.

The 5+0 material, for the record, since it is new to the corpus at this volume:
chess.com Jan–Apr 2024 at 5+0 is 2,074 eligible moves at 6.56% floored
(`hungself` 2.03%); Lichess 2024 at 5+0 is 502 eligible at 4.58%
(`hungself` 1.79%). Both sit with their own era rather than with their format,
which is what the pooling default predicts.

### Clock spend is a property of the player, not the site

Both sites were 3+2 in the date-matched windows, so per-move time spend compares
directly and needs no evals. Mean seconds per own move, Sept–Dec 2024:

| moves | 1–5 | 6–10 | 11–15 | 16–20 | 21–25 | 26–30 | 31–35 |
|---|---|---|---|---|---|---|---|
| Lichess | 2.2 | 5.2 | 7.6 | 7.9 | 6.9 | 5.8 | 4.2 |
| chess.com | 2.2 | 5.3 | 7.7 | 8.4 | 7.3 | 5.7 | 3.9 |

Band for band, indistinguishable. The spend peak at moves 11–25 — the standing
clock-management question — is a habit, not an artifact of one site's interface
or pool. Reproduce with `blockstats.py clock`.

### Reproducing the statistics

`longitudinal.py` gives per-block rates with bootstrap CIs. It does not give
significance, and reading it off overlapping CIs is unreliable. `blockstats.py`
does the tests; every p-value in this README comes from it, with the seed noted.

It carries two families of metric with **different denominators**: `hang` and
`hungself` are per eligible winning-middlegame move, while `reached`, `noelig`
and `reached_mg` are per game and mirror `outcomes.py`'s eligibility (no `cp`
gate). Do not compare across the families.



```bash
# do any of the six Lichess blocks differ?  spread 0.92 pp, p = 0.86
# (five blocks, before Q4 2025 was annotated, gave the same spread at p = 0.71)
python3 chess/scripts/blockstats.py shuffle \
    2024H2=h2.pgn Q1=q1.pgn Q2=q2.pgn Q3=q3.pgn Q4=q4.pgn 2026=corpus.pgn \
    --tc 180+2 --metric hang --seed 23

# was the June 2025 dip real?  minimum-block p = 0.13, spread p = 0.20
python3 chess/scripts/blockstats.py shuffle \
    Apr=li_202504.pgn May=li_202505.pgn Jun=li_202506.pgn \
    --tc 180+2 --metric hang --seed 17

# lichess vs chess.com, date-matched:  hungself +0.53 pp, p = 0.10
python3 chess/scripts/blockstats.py pools \
    '2024:li=h2_sepdec.pgn' '2024:cc=cc_2024q4_analyzed.pgn' \
    '2026:li=li_2026febapr.pgn' '2026:cc=cc_2026febapr_analyzed.pgn' \
    --tc 180+2 --metric hungself --seed 41 --user-map li=jamorgan cc=justinmorg
```

Two rules the subcommands encode, both learned the hard way here:

- **`shuffle` reports two p-values.** Use the minimum-block one when a block was
  singled out *because* it was extreme; use the spread one to ask whether any
  block differs at all. Quoting the wrong one is how the June dip nearly became
  a finding.
- **`pools` shuffles within window.** Never compare a pooled multi-year baseline
  against a date-specific block. Doing so absorbs between-block noise into the
  contrast; it turned p = 0.10 into p = 0.031 once already.
- **`shuffle` takes one `--user` for all blocks; only `pools` accepts
  `--user-map`.** Passing `--user NAME=account` to `shuffle` does not error — it
  sets the username to the literal string `NAME=account`, every game fails the
  match, and the run dies with a `KeyError` on the first block name while
  printing a table header first. For an all-chess.com `shuffle`, set
  `CHESS_USER=justinmorg` (or `--user justinmorg`) for the whole invocation.
  Mixed-site comparisons have to go through `pools`.

Eligibility mirrors `longitudinal.py` exactly, so block rates printed by the two
scripts agree. Note the diversity tests in the chess.com section used
rarefaction on top of permutation, since those metrics depend on sample size;
`blockstats.py` does not implement that, and the rates it handles do not need it.

### A cross-pool difference that did not hold up

Recorded because it was pushed as suggestive and then failed a better test.

Pooling the five Lichess blocks (licensed by the homogeneity result above)
against the chess.com Sep–Dec 2024 block gave `hung it myself` 1.15% vs 1.66%,
+0.51 pp, p = 0.031, while overall hanging material did not differ. The obvious
follow-up was a second, independent chess.com sample, so Feb–Apr 2026 was
annotated (137 games).

It came in *higher still* — 2.86% [1.52, 4.38] — which looked like confirmation.
It isn't. Two date-matched windows, permuting pool labels **within** window so
that time cannot stand in for pool:

| window | pool | games | eligible | hanging | hung it myself |
|---|---|---|---|---|---|
| 2024 Sep–Dec | Lichess | 273 | 821 | 5.48% | 1.22% |
| 2024 Sep–Dec | chess.com | 808 | 2,650 | 5.51% | 1.66% |
| 2026 Feb–Apr | Lichess | 433 | 1,506 | 5.25% | 1.39% |
| 2026 Feb–Apr | chess.com | 137 | 525 | 4.95% | 2.86% |

- hanging material: cc − li = +0.09 pp, **p = 0.88**
- hung it myself: cc − li = +0.53 pp, **p = 0.10**

The direction is consistent across both windows (+0.44 and +1.47 pp), but it is
not significant once time is controlled.

**A third window closed this further (Aug 2026).** Annotating the 2023 blocks on
both sites made a Jun–Jul 2023 window available — the only period before 2024
where both accounts were active — so the test now runs on three windows:

| window | pool | games | eligible | hanging | hung it myself |
|---|---|---|---|---|---|
| **2023 Jun–Jul** | **Lichess** | **432** | **1,346** | **7.43%** | **2.38%** |
| **2023 Jun–Jul** | **chess.com** | **225** | **590** | **7.46%** | **3.05%** |
| 2024 Sep–Dec | Lichess | 273 | 821 | 5.48% | 1.22% |
| 2024 Sep–Dec | chess.com | 808 | 2,650 | 5.51% | 1.66% |
| 2026 Feb–Apr | Lichess | 433 | 1,506 | 5.25% | 1.39% |
| 2026 Feb–Apr | chess.com | 137 | 525 | 4.95% | 2.86% |

- hanging material: cc − li = **−0.36 pp, p = 0.55**
- hung it myself: cc − li = **+0.33 pp, p = 0.41** (was +0.53 pp, p = 0.10)

Adding the window **weakened** the `hungself` contrast rather than sharpening
it — the effect size fell by nearly half and p went from 0.10 to 0.41. The
direction is still positive in all three windows (+0.68, +0.44, +1.47 pp), but a
difference that shrinks as data arrives is behaving like noise, not like a real
effect waiting for power.

The 2023 window is also a **third independent replication of the
hanging-material equivalence**, and the most surprising one: 7.43% against
7.46%, with the two accounts at ~929 and ~646 nominal Elo. The cross-pool rate
agreement holds at the beginner end of the range as well as the settled end.

The window is deliberately cut to Jun 14 – Jul 31 rather than to the full
overlap of the two blocks. chess.com has no games Aug–Oct 2023, so a Jun–Oct
window would compare four Lichess months against two chess.com ones and
re-introduce exactly the time-leakage this test exists to prevent. The looser
cut gives +0.30 pp at p = 0.46 — same conclusion, worse hygiene.

**Why the pooled test overstated it.** Pooling the whole Lichess corpus put the
baseline at 1.15%, but the two date-matched sub-windows sit at 1.22% and 1.39%.
The homogeneity result says that spread is noise — which is exactly the point:
it is noise the pooled comparison silently absorbed into the *contrast*.
Homogeneity licenses pooling for comparisons *between* Lichess blocks. It does
not license using a pooled Lichess baseline against a block drawn from specific
weeks. Match the dates.

**Status: still open, leaning null, and no longer cheaply advanceable.** The
422 previously un-annotated chess.com 3+2 games have since been annotated, with
533 more at 5+0, taking chess.com from 3,175 to 6,511 eligible moves — roughly
double — and the contrast got *smaller*. There is nothing left to annotate at
these formats on either site.

What remains is 1,072 chess.com games at **3+0**, which is not verified as
poolable and would need that verification first. Beyond that this needs new
chess.com 3+2 play, not new analysis of existing games. Given that doubling the
sample roughly halved the effect, the honest expectation is that there is
nothing here.

One observation worth keeping, on small numbers: in the 2026 chess.com block the
composition inverts — 15 of 26 floored hits are `hung it myself` against 11
`missed their threat`. Every other block measured, on either site, is roughly
3:1 the other way. It was flagged as the thing to look at first if more
chess.com data arrived, so: **it arrived, and it half-holds.** The Jan–Apr 2024
3+2 block also inverts (11 `hung it myself` against 9 `missed their threat`,
on 20 floored hits), but the 2023 block does not (29 against 46, the usual
direction) and neither does the same period's 5+0 material (42 against 94).
Two small inverted blocks out of five is not a pattern; it is what 20-hit
samples do. Treat the inversion as unexplained and uninteresting until some
block with real weight shows it.

### The 2023–2024 file needs filtering before use

`jamorgan_blitz_2023_2024_raw.pgn.gz` is every rated blitz game from
2023-03-19 to 2024-12-30, pulled 2026-08-24. Raw — clocks on every ply, no
evals. **Do not use it whole.** Four things have to be handled:

| | |
|---|---|
| Games | 1,642 |
| Date range | 2023-03-19 20:13:01 → 2024-12-30 17:54:29 UTC |
| Plies | 101,388 |
| Event type | 1,638 `rated blitz game` + 4 `≤1700 Blitz Arena` |
| Results | 823 W / 747 L / 72 D (raw `Result` tag) |
| Eval coverage | **0 / 101,388 plies** |
| Clock coverage | 101,388 / 101,388 plies |
| Duplicate GameIds | 0 |

**1. The first ~60 games are rating calibration, not play.** The account opens
at Lichess's default 1500 and falls to ~820 within 40 games. Mean absolute
rating change per game: ±51.1 over games 1–20, ±13.6 over 21–40, ±7.8 over
41–60, then ~±5–6 from game 61 on. Lichess does **not** mark these provisional
in the PGN — no `?` on the Elo tags — so the only signal is the change
magnitude. Including them makes April 2023 (mean 818) look like a collapse from
March (mean 1137) when it is just the system converging.

**2. Coverage is scattered, not continuous — but this is not inactivity.**
Zero games in Nov–Dec 2023 and Mar–May 2024; June 2024 has one. It is tempting
to read that as ~17 months of activity inside a 22-month window. That reading
is **wrong**: the chess.com export (see below) shows 463 games in Nov 2023 and
2,517 in Jan–May 2024, against 196 on Lichess over that same Jan–May stretch.
The gaps are platform switches, not breaks in play. Treat every Lichess volume
figure as a lower bound on what was actually played, and see the chess.com
section for which windows are recoverable.

**3. Four time controls, two of them absent from every later file.** 3+2
(1,247), 3+0 (151), 5+0 (136), 5+3 (108). The pooling default documented below
was verified for 3+2 vs 5+0 only. 3+0 is a harsher clock regime than anything in
2025–2026 and is concentrated in Jan–Feb 2024.

**4. Four arena games.** Both other files are 100% `rated blitz game`; filter
`Event` to match.

After filtering to 3+2, non-arena, post-calibration, two clean blocks remain:
2023 Apr–Jul (~495 games, rating ~820 → 1000) and 2024 Aug–Dec (651 games,
rating ~1234 → 1301).

**Both are now annotated, and so is everything else at 3+2 or 5+0 in this
file** — see "Complete 3+2 / 5+0 coverage" above. `jamorgan_blitz_2023` (596
games) and `jamorgan_blitz_2024rest` (132) between them cover every non-arena
3+2/5+0 game the 2024 H2 block does not. Points 1 and 4 above still describe the
raw file, but they are now **analysis-time** filters rather than reasons to skip
data: calibration games are deliberately included in the 2023 block, so exclude
them by date if a question needs them out, and the 4 arena games are excluded
from the annotated blocks entirely.

The earlier reason for skipping 2023 — that 800–1000 Elo is just a beginner
improving and says little about the plateau — was right about the plateau and
wrong about the value. It says nothing about *why* the plateau exists, but it
turned out to be the only available positive control on whether the
hanging-material measure can detect change at all. See "The positive control:
this metric does move".

### Time control changed mid-2026

The 2025 and 2026 files span different time controls. 2025 is essentially all
3+2 (2,527 of 2,529). 2026 is roughly half each — 3+2 through April, 5+0 from
May onward, with the switch complete by August. (2023–24 is messier still; see
above.)

**Default: pool them.** Verified on the 2026 corpus, where both formats have
~750 games:

- Opening-phase eval after move 12 is indistinguishable: +49cp [28, 71] in 3+2
  vs +60cp [39, 81] in 5+0; share at ≤−100cp is 22.4% vs 19.8%. Fully
  overlapping.
- Seconds spent per move is near-identical through move 25 (peak 8.4s vs 7.8s
  at moves 16–20). Clock *behaviour* is format-independent; only the budget
  differs.
- 75% of group P positions are at move ≤25, 90% at ≤30 — inside the comparable
  window.

**Exception: clock state past move ~25–30.** The 3+2 increment floors the median
clock at ~18–20s from move 40 on; 5+0 keeps a larger cushion but has no floor
(10th percentile at move 60 is 3s). Losses on time are similar in both (4.55%
vs 4.99%) by different mechanisms. Split by `TimeControl` for anything
clock-dependent late in the game, and check CI overlap before pooling.

## The chess.com corpus

`justinmorg` on chess.com is the same player. The account predates nothing —
Lichess starts 2023-03-19, chess.com 2023-06-14 — but it ran *concurrently* with
Lichess for most of the project's history, and during several stretches it was
the primary site. Any question of the form "what was he doing in <month>" needs
both.

Raw monthly exports are pulled from chess.com's archive endpoint and filtered
with `chesscom_filter.py`:

```bash
python3 chess/scripts/chesscom_filter.py cc_blitz.pgn ChessCom_justinmorg_*.pgn
```

The raw exports mix everything the account played that month into one file, and
three of those things will silently corrupt any analysis:

1. **Time-control classes have separate rating pools.** Blitz, bullet and rapid
   each carry their own chess.com rating. Pooling them makes the Elo tags
   meaningless — including rapid made April 2024 read as Elo 972 when the blitz
   rating that month was 686. The filter keeps blitz only, classed by
   `base + 40*increment` (<180s bullet, 180–599s blitz, ≥600s rapid).
2. **Within blitz, formats do share one pool.** Verified: in months mixing 3+0,
   3+2 and 5+0, mean Elo per format sits within ~10–30 points, and the mean
   absolute rating change between consecutive games is the same whether the
   format switched or not (7.4 vs 7.9). So the blitz set is one continuous
   rating series and can be treated as such — but see the 3+0 caveat below.
3. **Variants and daily games are in there.** 29 variant games (Crazyhouse,
   Three-Check, Chess960) and 4 correspondence games, all dropped by `Event`.

### Verified contents of the filtered blitz set

Stored as `chesscom_justinmorg_blitz_raw.pgn.gz`: 2,977 games, 184,408 plies,
2023-06-14 → 2026-04-01, deduped on game id, no evals. Same relationship to
`chesscom_justinmorg_2024q4_analyzed.pgn.gz` as the Lichess `_raw` files have to
their analyzed slices — the 811 analyzed ids are a strict subset. Keep raw play
here rather than only in the monthly exports; the exports are not in the repo.

By block, with 3+2 counts:

| block | games | plies | formats | notes |
|---|---|---|---|---|
| 2023 Jun–Nov | 362 | 21,312 | 351 at 3+2 | **annotated** (359 incl. 5+0) — pre-repertoire, Englund absent entirely, Caro 16% in Jun–Jul |
| 2024 Jan–Apr | 1,667 | 100,969 | 1,071 at 3+0, 525 at 5+0 | **3+2 and 5+0 annotated** (596); the 3+0 remainder is not | 
| 2024 Sep–Dec | 811 | 52,097 | 808 at 3+2 | **annotated** — see below |
| 2026 Feb–Apr | 137 | 10,030 | all 3+2 | concurrent with the 2026 corpus |

Nothing between 2025-01 and 2026-01 was exported. A July 2025 file exists (~6
games at Elo 754–827) but failed to transfer three times; it is not in this set.

The Jan–Apr 2024 block was the largest single body of unanalysed play anywhere
in this project, and it fills a genuine Lichess hole. Its 3+2 (71) and 5+0 (525)
games are now annotated as `chesscom_justinmorg_2024janapr`. What is left of it
is **1,072 games at 3+0**, the one clock regime this project has never verified
as poolable — that remainder still needs its own comparison, not a row in the
existing table.

**Every 3+2 and 5+0 game on either site is now annotated.** The un-annotated
remainder across the whole project is exactly the formats deliberately out of
scope: 3+0 (1,072 chess.com, 151 Lichess), 5+3 (108 Lichess), 300+2 (2
chess.com) and 4 Lichess arena games.

### `chesscom_justinmorg_2024q4_analyzed.pgn.gz`

811 games, 52,097 plies, 2024-09-02 → 2024-12-27. Depth-12, same engine and
output format as every other analyzed file.

| | |
|---|---|
| Games | 811 |
| Plies | 52,097 |
| Event type | `Live Chess` (all 811) |
| Time control | 808 at 180+2, 3 at 300 |
| Results | 413 W / 371 L / 27 D (raw `Result` tag, not per-colour) |
| Eval coverage | 52,097 / 52,097 plies |
| Clock coverage | 52,097 / 52,097 plies |
| Duplicate GameIds | 0 |
| Mean rating / opponent | 774 / 774 |

It was annotated because it is date-matched to the Sept–Dec portion of the
2024 H2 Lichess block, at the same time control, in a different pool — making it
a direct replication test of the finding this whole project rests on.

**It replicates.** Restricted to 3+2, Sept–Dec 2024 both sides:

| | Lichess | chess.com |
|---|---|---|
| games | 273 | 808 |
| eligible winning-middlegame moves | 821 | 2,650 |
| hanging material (0.02 floor) | 5.48% [4.02, 7.06] | 5.51% [4.64, 6.38] |
| blunder rate, moves 1–12 | 3.80% | 3.79% |
| blunder rate, moves 26+ | 12.65% | 13.51% |
| reached ≥+200 in middlegame | 53.5% | 55.6% |
| score from won positions | 61.3% | 63.7% |
| mean opponent Elo | 1290 | 774 |

A 516-point nominal rating gap and effectively identical error rates. Two
consequences worth keeping:

- The plateau is **not a Lichess matchmaking artifact**. It reproduces in an
  independent pool.
- The gap between the two account ratings is **pure pool calibration**. Do not
  read a chess.com Elo as a weaker version of the player; read it as the same
  player on a different scale.

The chess.com blitz series independently shows the same shape over three years
(≈616 mid-2023 → 825 end-2024 → 906 early-2026): a climb through 2024 and a much
shallower stretch after. That is a second, independent sighting of the plateau.
Treat the 2026 figures with care, though — the account was dormant for ~14
months and the first ~20 games back are rating-deviation reconvergence (mean
|delta| 15.8, settling to ~7.2), the same class of artifact as the 2023 Lichess
calibration note above.

**One thing that may not replicate, and it has weakened.** `hung it myself`
comes in at 1.66% [1.21, 2.19] on chess.com. When this was written the Lichess
comparison was 1.00 / 1.06 / 1.08 / 1.06 across four blocks and the chess.com
interval's lower bound cleared three of those four point estimates. With Q2 and
Q4 2025 annotated the Lichess series is **1.00 / 1.06 / 1.30 / 1.08 / 1.44 /
1.06** and that lower bound now clears only four of six — Q2 (1.30%) and Q4
(1.44%) sit above it. The date-matched Lichess figure of 1.22% [0.49, 2.07]
overlapped it already. So this remains a flag to watch as more chess.com blocks
are annotated, and it is a weaker one than it looked: the apparent Lichess
"stability" it was contrasted against was partly an artifact of which four
blocks existed at the time. A six-block shuffle on `hungself` returns p = 0.86,
so the Lichess spread itself is noise — which cuts both ways, but it means the
1.00–1.08 band was never the right thing to measure chess.com against.

### Two format differences from the Lichess files

**Clocks carry tenths.** chess.com emits `0:03:02.6` where Lichess emits
`0:03:00`. These are kept as-is — no script in this pipeline parses `[%clk]`, and
the precision is real information for clock work. So a comment in a chess.com
file reads:

```
{ [%eval 0.34] [%clk 0:03:02.6] }
```

**`GameId` is injected.** chess.com does not emit one, but `annot_inc.py`
resumes by it, `merge.py` dedupes by it, and the drill tick keys are
`{mode}-{gid}-{ply}`. `chesscom_filter.py` writes `cc` + the numeric id from the
`Link` tag, e.g. `cc109056146404`. Deliberately: no hyphen, so it cannot corrupt
a tick key; the `cc` prefix makes provenance visible at a glance in stored
progress; 14 chars against Lichess's 8, so collision is impossible.

### Two hypotheses this corpus tested and did not support

Both were long-standing intuitions about chess.com vs Lichess. Neither survived.

**"I play worse on chess.com."** Disproved for playing *strength*: the Sept–Dec
2024 replication above shows identical error rates, blunder profile and
conversion across the two pools. What that does not rule out is a difference in
some period not yet measured — the test is date-matched to one window. The
516-point rating gap is pool calibration, nothing more.

**"chess.com players play more diverse positions."** Tested on 1,651
date-matched games — Sept–Dec 2024 (273 Lichess / 808 chess.com) and Feb–Apr
2026 (433 / 137), 3+2 only. Diversity was computed from the *moves*, not from
`ECO`, because the two sites classify openings with different books and the tags
are not comparable. Stratified permutation test, 400 permutations, rarefied to
250 games per stratum, permuting within window so period cannot leak in:

| metric | Lichess | chess.com | p | detectable at |
|---|---|---|---|---|
| distinct positions at ply 6 | 46.8% | 46.9% | 0.97 | ±5.1pp |
| distinct positions at ply 10 | 78.3% | 78.4% | 0.98 | ±4.6pp |
| distinct positions at ply 16 | 97.6% | 96.7% | 0.48 | ±2.2pp |
| opponent's 1st move, distinct | 7.5 | 6.8 | 0.55 | ±2.2 |
| opponent's 1st move, norm. entropy | 0.53 | 0.48 | 0.17 | ±0.07 |
| median divergence ply | 8.0 | 8.4 | 0.29 | ±0.75 |

Nothing significant; the last column is the point, since a null result is only
worth anything with a stated resolution. A difference of ~11% relative in
early-position variety would have surfaced. Every estimate that leans at all
leans toward *Lichess* being marginally more varied.

The other reading of "diverse" — messier positions rather than wider openings —
was tested separately on eval volatility (cp per ply, moves 13–25), material
imbalance at move 20, non-pawn material at move 20, queens-off-by-move-20 rate
and game length. All null.

**The intuition is real, but it is about `justinmorg`, not his opponents.**
Repertoire adherence by era, both sites, 3+2 only:

| block | London as White | Caro + Englund as Black |
|---|---|---|
| 2023 Jun–Jul | 79% cc / 84% li | **16% cc / 13% li** |
| 2024 Sep–Dec | 88% / 92% | 91% / 87% |
| 2026 Feb–Apr | 91% / 90% | 89% / 90% |

In mid-2023 the Black repertoire was essentially absent — Englund appears once
in 212 Lichess games. It locked in some time between mid-2023 and Sept 2024. The
chess.com game set is weighted toward that unsettled era while the Lichess
corpus is weighted toward 2025–26, so chess.com genuinely does hold more varied
positions *in memory*. The near-identical 2023 figures on both sites are what
rule out the opponent explanation.

Methodological note for anyone re-running this: rarefaction CIs are useless when
the subsample approaches the pool size. Drawing 263 games from a pool of 273
returns nearly the same games every time, which produced spuriously tight
Lichess intervals on the first pass and an apparent Lichess-is-more-diverse
effect that vanished once a permutation test replaced it. Permute group labels;
don't compare rarefaction intervals across unequal pools.

### `CHESS_USER` — read this before running anything on chess.com data

`hanging.py` and `longitudinal.py` identify the player by username and **skip
every game that doesn't match**. Both defaulted to a hardcoded `jamorgan`, so
pointing either at chess.com data produced a clean, silent zero.

Both now read the `CHESS_USER` environment variable, defaulting to `jamorgan`:

```bash
CHESS_USER=justinmorg python3 chess/scripts/hanging.py cc_2024q4.pgn light
CHESS_USER=justinmorg python3 chess/scripts/longitudinal.py CC=cc_2024q4.pgn --tc 180+2
```

`hanging.py` additionally hard-exits if a file yields games but no matching ones,
rather than reporting an empty result. Verified behaviour-neutral for the
Lichess path: it still reproduces 368 hits (290/78) on the 2026 corpus exactly.

Group P drills are still built from Lichess positions only. Mixing pools into
the drill set is a live decision, not something the current
`build_drills2.py` does — and it would change the counter denominator, so read
the tick-key section before attempting it.

## Every eval is local depth-12 Stockfish 16

The whole corpus is uniform local analysis at depth 12 — **no Lichess server
evals anywhere.** Keeping it uniform is the point: mixed analysis depths make
threshold-crossing statistics meaningless, since a position's eval would depend
on whether Lichess happened to have analysed that game.

So if a fresh download arrives with server evals attached, **overwrite them with
`annotate.py` rather than keeping them.** `annotate.py` already does this — it
replaces any existing `[%eval]` and preserves the `[%clk]`.

### Depth-12 caveat

Depth 12 is reliable at the **+2** threshold. It is **noticeably noisy at +5**,
because positions that far ahead tend to be tactical, and tactical positions are
exactly where shallow search misjudges. Roughly **6% of plies flip across the +5
line** between depth 12 and deeper analysis.

Practical rule: any finding that leans on +5 should be re-checked at higher
depth on the specific positions involved. Findings at +2 can be taken at face
value.

### Individual evals can also just be wrong

Separate from depth noise: a small number of `[%eval]` values in the annotated
files are simply corrupt — not a shallow-search misjudgment but a number that
no engine at any depth produces for that position. Found Aug 2026 by reading a
group R card that looked wrong: game `bdWcvWUA` ply 25 (13.Bf3) carries −602,
while fresh Stockfish gives −0.17 at depths 12, 16 and 20, and the corpus's own
next own-move row snaps back to +31. The game was won, peak +546. One bad
number invented a permanent 650cp collapse.

Rate, measured rather than assumed: re-evaluating the position after the played
move for all 330 thread-2 judgment positions found **one** gross disagreement —
this one, off by 585cp. The next-largest gap was 145cp, ordinary depth-12
wobble. So roughly 0.3%, and no published figure moves when it is dropped (H2
shifts ~0.1 pp; the thread 2 shares not at all). **Deliberately not fixed** — no
blacklist, no re-annotation. At this rate the machinery would cost more than the
error.

What this does mean:

* A single position that looks obviously wrong probably *is* wrong. Check it
  against a live engine before theorising about it.
* Don't build an argument on one position. Every finding in this README rests on
  hundreds of rows, where a 0.3% artifact rate is harmless.
* If a future analysis ever does turn on individual plies, audit first — the
  fresh-eval comparison above is a few minutes of engine time.

## Update procedure

### When it is worth pulling a fresh batch

Written Aug 2026, because "download the newest games" is the default reflex and
it is usually **not** worth doing. A new block costs engine time and, worse,
adds another opportunity to find a spurious difference — the corpus already has
three retracted findings and one untested flag, every one of them from a small
block. Q4 2025 is the cautionary case: 232 games bought a hanging-material
interval of [2.89, 5.92] and resolved nothing.

Current baseline for the arithmetic: **~190 games/month** (2026 average; recent
months run 190–325) and **~3.3 eligible winning-middlegame moves per game.**

**Pull a fresh batch when any one of these is true:**

1. **Volume.** ~900+ new games since the last block, which is ~3,000 eligible
   moves — the point at which a block gets a ±0.6 pp interval and can actually
   sit in the flatness table. At current volume that is **roughly 5 months of
   play.** Below ~450 games (~1,500 eligible, ±0.9 pp) a new block cannot
   distinguish anything from the existing 4.3–5.2% band and should not be
   annotated as a separate block at all — fold it into the next one.
2. **Rating regime change.** The rating leaves the **1310–1455** plateau band
   and stays out. Stated so it can be checked by eye, without computing
   anything — see "Checking the rating trigger by eye" below. This is the one
   trigger that justifies a small block, because a regime change is worth
   measuring even at low precision.
3. **A specific question needs it.** Not "let's see if anything changed" — an
   open thread that a new block would actually settle.

**Do not pull a batch just because time has passed.** As of 2026-08-19 the
trailing-200 mean is **1370**, dead centre of the band, and 2026's monthly means
run 1419 / 1454 / 1395 / 1353 / 1310 / 1362 / 1401 / 1368 — the full width of
the band, oscillating, no trend. Movement inside that band is not a signal; the
band *is* the signal, and it has been flat for ~13 months.

### Checking the rating trigger by eye

Trigger 2 was originally written as "trailing-200-game mean leaves the band,"
which is correct and useless — nobody can compute a trailing-200 mean from
the Lichess profile page, and no session of this project has network access to
Lichess or chess.com to compute it either (both hosts are blocked by the
environment's egress policy). Restated as something checkable in five seconds:

> **If the rating is outside 1310–1455 every time you look, for three weeks
> straight, it is worth a fresh batch. Otherwise ignore it.**
>
> **Override:** a single reading below **1250** or above **1520** is worth
> flagging immediately, without waiting out the three weeks.

**1310–1455 is a monthly-mean band and must not be read instantaneously.**
Point-in-time rating swings far wider. Over the plateau (2025-07-01 →
2026-08-19, 2,110 games) it ranged **1262 to 1508** and sat outside the band on
**10.7% of games** — so a random glance at the profile has a better than 1-in-10
chance of showing "out of band" with nothing having changed. The band is fine;
the persistence requirement is what makes it usable.

Why three weeks, calibrated on that same known-flat stretch — 33 separate
excursions outside the band, of which:

| excursion | days | games | direction | extreme |
|---|---|---|---|---|
| 2026-02-04 → 02-14 | 9 | 48 | high | 1508 |
| 2026-05-16 → 05-25 | 8 | 36 | low | 1262 |
| 2026-05-05 → 05-10 | 5 | 23 | low | 1272 |
| all 30 others | ≤ 1 | | | |

Nothing stayed out for 10 days. A **14-day** rule would have produced zero
false alarms across the whole plateau; **21 days** is the recommendation because
it gives better than 2× margin over the worst observed excursion, and because
spot-checking is weaker evidence than the continuous game-by-game series these
numbers come from — an excursion can dip back inside the band between two
glances and never be seen.

So **check weekly, not twice.** Three or four looks spread across the three
weeks, all outside the band, all on the same side. The cadence supports it:
5.1 games/day, play on 75% of days, and the longest no-play gap in 13 months
was 6 days — so "it has been out for three weeks" can never just mean "I did
not play." Three weeks is ~110 games.

The override thresholds are set outside everything 2,110 plateau games
produced (min 1262, max 1508). A reading past them is unprecedented rather
than merely unusual, so there is nothing to wait for.

The largest excursion in that table — 2026-02-04 → 02-14, peaking at 1508 — has
since been tested directly rather than assumed, and is noise: no move-quality
metric moved. See "The Jan/Feb 2026 rating peak was a random walk". If trigger 2
ever does fire, run `ratingexcursion.py` on the existing corpus before
annotating anything new; it is minutes of work and may settle the question
without a new block.

Reproduce the calibration from the committed blocks — Q3 2025 onward, own Elo
per game, runs of consecutive games outside the band measured in calendar days.
Re-derive it if the band is ever revised; the 21 days is a property of this
band and this rate of play, not a constant.

The marginal value of another same-era block is now genuinely low. Flatness
holds at p = 0.86 across six Lichess blocks, and the beginner-era blocks supply
the positive control showing the measure moves when skill does. A seventh
settled block would add a seventh null.

**The natural next batch** is the rest of 2026: the corpus ends 2026-08-19, and
Sep–Dec at current volume is ~760 games, so closing out the calendar year some
time in Jan 2027 would produce a properly-sized block on a clean boundary. That
is the default plan unless trigger 2 or 3 fires first.


1. **Find the latest timestamp in the corpus.**

   ```bash
   gunzip -c chess/data/jamorgan_blitz_2026_analyzed.pgn.gz \
     | grep -E '^\[UTC(Date|Time) ' | tail -2
   ```

   Convert that UTC timestamp to epoch milliseconds for the next step.

2. **Download new games** from the Lichess API:

   ```
   https://lichess.org/api/games/user/jamorgan?since=<epoch_ms>&perfType=blitz&rated=true&clocks=true&evals=true&opening=true&sort=dateAsc
   ```

   Lichess's `since` filter can include the boundary game, so the last game
   already in the corpus will often come down again. That's expected — step 4
   dedupes it by GameId.

3. **Annotate** at depth 12, overwriting any server evals that came with it:

   ```bash
   python3 chess/scripts/annotate.py new.pgn new_annotated.pgn --depth 12
   ```

4. **Merge.** Earlier files win on GameId collisions, so put the freshly
   annotated games *first* and the existing corpus second:

   ```bash
   python3 chess/scripts/merge.py corpus_v2.pgn new_annotated.pgn corpus.pgn
   ```

   `merge.py` prints the game count, duplicate count, and date range — check
   these before continuing.

5. **Re-gzip and push.**

   ```bash
   gzip -9 -c corpus_v2.pgn > chess/data/jamorgan_blitz_2026_analyzed.pgn.gz
   ```

### Stockfish in a fresh sandbox

`annotate.py` looks for the engine at `/home/claude/sf/x/usr/games/stockfish`,
overridable via the `STOCKFISH_PATH` environment variable. To install it where
there's no package manager access:

```bash
cd /home/claude && mkdir -p sf/x && cd sf
apt-get download stockfish && dpkg-deb -x stockfish*.deb x
```

Annotation is the slow step — it's a full depth-12 search per ply, parallelised
across cores by `--workers`. A few hundred new games is minutes, not seconds.

### Use `annot_inc.py` for anything over ~100 games

`annotate.py` holds all output in memory and writes once at the end, so a run
killed partway through loses everything. Sandboxes have a per-command time limit
and background jobs do **not** survive between commands — `nohup` does not help.
Two full annotation runs were lost this way before the wrapper existed.

```bash
python3 chess/scripts/annot_inc.py in.pgn out.pgn 240   # 240s budget, then exits
```

It annotates one game at a time, appends and `fsync`s after each, and resumes by
GameId — so re-run it until it prints `DONE n/n`.

It splits input with `annotate.split_games`, **not** on `'\n\n\n'`. Files here
are inconsistent about blank lines between games: the analyzed slices use two,
the canonical 2026 corpus uses one. A `'\n\n\n'` split returns the entire corpus
as a *single* block with no error — it then fails to parse as one game and
annotates nothing. It also exits with a clear message on a game with no
`GameId`, since resuming is impossible without one, rather than raising an
`AttributeError` from deep inside a lambda. Same depth-12 engine call and
same output format as `annotate.py` (it imports `fmt_eval`/`ENGINE`/`CLK_RE`
from it), so the two are interchangeable in the corpus.

Measured throughput, single core: **~2.9 s/game, ~24 plies/s.** That's ~120
games per 240s call. Budget accordingly — a full calendar year of this corpus is
hours.

### Don't commit `__pycache__`

Importing `hanging.py` or `annotate.py` from a sibling script writes `.pyc`
files into `chess/scripts/__pycache__/`. These are *untracked*, so a
`git checkout` before pushing does not remove them and they get swept into the
commit. `chess/.gitignore` now covers this; if bytecode still appears in
`git status`, remove it rather than committing it.

### When GitHub Pages won't deploy

Symptom (hit Aug 2026): `actions/deploy-pages` polls forever printing an empty
`Current status:`, and re-running the workflow just produces another failure.
The Pages API tells the real story where the Actions log doesn't:

```python
GET /repos/justinmorg/justinmorg.github.io/pages          # -> "status": "errored"
GET /repos/justinmorg/justinmorg.github.io/pages/builds   # -> per-build status + duration
```

**Duration 0 with a bare "Page build failed" means the build never started** —
infrastructure, not content. A real Jekyll or content error takes seconds and
names a file, and this repo has `.nojekyll` at root anyway, so files are copied
verbatim and there is nothing for a build to choke on. Six consecutive builds
failed this way while the page itself was fine.

The wedge is bound to the **commit SHA**, not the repo: every failure was
against the same two SHAs, whose deployment records were stuck from the moment
the first one queued. Retrying either kept hitting the same dead record.

Fix, cheapest first:

```bash
git commit --allow-empty -m "chore: fresh Pages deployment record" && git push
```

A new SHA gets a clean record. That worked immediately — 20s build, status back
to `built`. Only if it doesn't: toggle Settings → Pages source off and back
(this repo is `build_type: legacy`, branch `main`, root), or wait out GitHub's
24-hour auto-cancel of stuck queued runs. **Don't keep pressing re-run** — each
retry adds another run to the same jammed queue.

Note that Pages publishes the *current state of the branch*, not a replay of
each commit, so one successful deployment ships every commit behind it. Stale
`queued` runs left in the Actions tab afterwards are inert.

## Hanging-material extraction

`hanging.py` finds the largest single source of thrown-away wins: middlegame
moves played while already winning, with material hanging.

```bash
python3 chess/scripts/hanging.py corpus.pgn light   # -> /home/claude/hits_light.json
python3 chess/scripts/build_drills2.py              # -> chess-drills/index.html
```

`build_drills2.py` takes `hits_light.json` and the page path as optional
arguments, both defaulting relative to its own location in the repo, so it runs
from any clone directory. It applies the 0.02 floor itself. Verified: running it
against a freshly regenerated `hits_light.json` reproduces the committed
`index.html` byte for byte.

Selection, for `jamorgan`'s moves only:

- middlegame — `fullmove > 12` and non-pawn material `> 14` on the **light**
  scale (N/B=1, R=2, Q=4, so 24 at the start). The 3/3/5/9 scale is *not* the
  right reading of that threshold: 14 there would admit R+N vs R+N endings.
- eval before the move `>= +150cp` from jamorgan's POV
- the opponent has a capture with SEE `>= +150`, either already available
  (`missed their threat`) or created by the move (`hung it myself`)

Two things that are easy to get wrong and are handled explicitly:

- **Recaptures are netted.** After a capture, the opponent's recapture scores a
  big raw SEE even for a dead-even trade. For the square the move captured on,
  the whole swap is scored by `see(before, move)` instead. Without this the hit
  count roughly triples and self-inflicted hangs are massively overcounted.
- **The null-move threat probe runs even when in check.** A piece can hang
  *and* the king be attacked; skipping the probe there silently relabels every
  such position as self-inflicted.

### Rerunning this in a fresh sandbox

- **`python-chess` is not preinstalled:** `pip install chess --break-system-packages`
  (1.11.2 as used here). Separate from the Stockfish install below — `hanging.py`
  needs no engine at all, only the PGN's existing evals.
- **`attackers_mask(color, square, occupied)` is public and takes an occupancy
  bitboard.** There is no `_attackers_mask`. SEE needs the occupancy argument to
  see through x-rays; without it, batteries score wrong.
- **Unit-test SEE before trusting a run.** `test_see.py`-style hand-built FENs
  are the likeliest thing to be wrong, not the algorithm — check which squares a
  pawn actually defends before calling a mismatch a bug.
- **Apply the 0.02 win%-error floor for drill sets.** 129 of the 368 hits cost
  essentially nothing: SEE finds material, the eval doesn't move, because there
  was compensation (a bigger capture elsewhere, a check, a counter-threat). They
  meet the criteria but the correct answer in them is "ignore it," which is the
  opposite of the reflex the drills train.

### Don't chase the older "264" figure

An earlier session reported 264 such moves (217 missed / 47 self-inflicted) on a
1,431-game corpus. That number is not reproducible from this pipeline and its
script wasn't kept. The current pipeline gives **368** on 1,515 games (290/78),
of which **239** clear the 0.02 floor (184/55). The 79/21 split is close enough
to the old 82/18 to suggest the same phenomenon, but treat the current numbers
as canonical and don't tune filters to hit the old one.

Counts are baked into `chess-drills/index.html` (drill totals, game count, the
localStorage total). Regenerate with `build_drills2.py` rather than
hand-editing.

### Tick keys, and why `build_drills.py` must not be run

Progress lives in `localStorage` under `drills.done.v1`, one key per drill.

- Endgame drills are `1`…`21`. Unchanged since the page was created.
- Priority drills are `{mode}-{gid}-{ply}` — e.g. `A-xTjfTJRD-26`. **Stable
  ids**, derived from the game and the move, so reordering, refiltering or
  re-splitting the set leaves ticks attached to the right positions.

They were originally positional (`P1`…`Pn`), which meant any rebuild silently
shifted what each tick referred to. That changeover orphaned the existing `P`
ticks once — they're inert entries in the stored object now, harmless but
never matched. There should be no second reset.

The counter denominator is `260` = 239 priority + 21 endgame, set in
`build_drills2.py`'s output and in the reset confirmation string.

`build_drills.py` built the *first* version of the priority set (single P
group, positional keys, no on-page boards) by string-patching a pre-priority
`index.html`. Against the current page most of its anchors no longer exist and
would no-op, but the `id="gC"` section anchor still matches, so it would paste
a second complete priority block in with the old keys — ~500 cards, duplicate
element ids, counter still reading 260, and no error. It now hard-exits if the
page already contains `id="gP"`. It's kept for reference only; `build_drills2.py`
replaces the whole P block rather than mutating what's there, and is safe to run
repeatedly.

### Why this survives the depth-12 caveat

Selection is pure SEE — static move arithmetic, independent of search depth.
Only the win-probability ranking uses evals, and the Lichess logistic saturates
exactly where depth 12 is unreliable: 200cp of error is worth 17.6 win% points
at 0.00 but only 3.6 at +7.0. Re-ranking with every eval clamped to ±5 leaves
the top 50 **98% unchanged** and the full ordered set identical. So the +5
noise the caveat warns about does not move this finding.

## Position-level feature tables

`features.py` makes one pass over the annotated blocks and emits two flat
tables, so questions that used to need a bespoke PGN walk become a groupby.

```bash
python3 chess/scripts/features.py \
  2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn 2026=corpus.pgn \
  CC-2024Q4=cc_2024q4_analyzed.pgn CC-2026=cc_2026febapr_analyzed.pgn \
  --tc 180+2,300+0 --user-map CC-2024Q4=justinmorg CC-2026=justinmorg \
  --out /home/claude/features
```

- `moves.csv.gz` — one row per **own** move; opponent moves appear as context
  columns, not rows. 178,684 rows over the seven blocks.
- `games.csv` — one row per game, 5,404 games.
- `manifest.json` — per block: path, resolved user, games read / matched /
  dropped and why, plies, eval coverage, date range, `--tc`, script SHA.

Runtime is ~100 s single-core for the whole set, including SEE probes and
complexity counts on every row. It regenerates faster than it can be
meaningfully version-controlled, so **the tables are not committed**;
`chess/.gitignore` covers `chess/data/features/`. Commit the script and the
manifest, not the CSVs.

Centipawns are player-POV throughout, matching `hanging.py`'s `cp_before_me`.
`mate_flag` marks rows where either endpoint is a `#N` score (±10000) — without
it a delivered mate reads as a ~9,800cp swing and destroys any mean it touches.

Definitions are imported from `hanging.py` and `outcomes.py` rather than
restated, so `elig_P`, peak/trough buckets and endgame-entry buckets agree by
construction. **Import `outcomes.bucket_of` downstream too** — reimplementing it
with `cp >= -100` instead of `-100 < cp` moves four games between `level` and
`losing`, which is enough to make a validation run look broken.

### It reproduces every published figure

Confirmed on the seven-block run: reached 2,865 / 63.9%; endgame entry
1,073 79.4% / 401 53.2% / 774 42.7% / 1,443 19.1%; flag wins 434 of 2,619 =
16.6%; per-block hang rates 5.02 / 5.21 / 4.40 / 4.31 / 5.51 / 4.95%. Anything
that disagrees is a bug in `features.py`, not a new finding.

Two expected differences, both scope rather than error:

- The 2026 hang rate reads **4.33%** here against **4.73%** in the table above,
  because that table is 3+2-only and this run is 3+2 *and* 5+0 — eligible moves
  go 2,640 → 5,517. Most tables in this README are narrower than the standing
  3+2/5+0 default. Check the scope line before comparing.
- Q1 2025 shows 1,228 eligible against 1,224, from a handful of 5+0 games the
  wider filter admits.

### The `block` column parses as an integer, and it corrupts exactly one block

`2026` is a valid integer literal; `2024H2`, `Q1-2025` and the rest are not. So
`pd.read_csv` on `moves.csv.gz` infers the `block` column's dtype **per chunk**
and lands on a mix of `int64` and `object`. A filter written the obvious way:

```python
m[m.block == '2026']        # silently matches only part of the block
```

returns whichever rows happened to be parsed as strings and drops the rest. It
emits a `DtypeWarning` about mixed types and nothing else. Read the column
explicitly:

```python
pd.read_csv(path, dtype={"block": str, "gid": str})
```

Found Aug 2026 while validating the Q4 2025 run: six of seven per-block hang
rates reproduced to the digit and **2026 alone** came back at 4.43% over 1,829
eligible moves instead of 4.33% over 5,517 — a third of the block, missing, in
the one block whose label is numeric. That looked exactly like a real
pipeline bug for about twenty minutes. `gid` has the same hazard (chess.com ids
are `cc`-prefixed and safe, Lichess ids are 8 chars and usually but not always
non-numeric).

Same family as the `CHESS_USER` and `Termination` failures: no error, a
plausible-looking table, and the only signal was that a published figure did
not reproduce. Validate against a known number.

### One row per game, without `groupby().apply()`

Sampling one move per game — needed constantly, since move-level rows are not
independent — fails in the pandas version here:

```python
pool.groupby('gid').apply(lambda d: d.sample(1))     # KeyError: ['gid'] not in index
```

The group key collides with the column of the same name, with or without
`group_keys=False`. Use shuffle-then-dedupe instead; it is also faster:

```python
pool.sample(frac=1, random_state=1).drop_duplicates('gid')
```

`forcingtest.py` builds its control set this way.

### The endgame-entry ply bug
`features.py` initially scoped endgame-entry detection to own moves. It belongs
**outside** the mover branch — `outcomes.py` has it there — because the endgame
is frequently entered by the *opponent's* move. Scoping it to own moves detects
entry one ply late, which shifts ~50 games between eval buckets and moved every
row of the endgame-entry table by 1–1.5 pp: `winning` read 1,123 / 78.3%
against the correct 1,073 / 79.4%.

The failure mode is worth remembering because it is silent and small. Nothing
errors, no count goes to zero, and the resulting table is plausible — the only
signal was that it didn't reproduce a published figure exactly. Same class as
the `CHESS_USER` and `Termination` failures: validate against a known number
before trusting a new pipeline.

### Guardrails

Each hard-exits rather than emitting a plausible-looking table:

1. Games read but none matching the user — the `CHESS_USER` silent zero.
2. Eval coverage below 100% — catches a `_raw` file fed in by mistake.
3. Zero flag games across all blocks — the chess.com free-text `Termination`
   failure, per `outcomes.py`'s precedent.
4. Duplicate `(gid, ply)` keys. A `gid` in more than one block warns rather than
   exits.

### Deliberately not columns

First-major-deterioration ply, phase bands and trajectory typologies are
groupbys on `moves.csv`, not stored fields. Their cutoffs will get argued over,
and baking them in means re-running the pass each time.

## Think time and error rate

The one crossing the corpus had never been run: seconds spent on a move against
whether that move was a blunder. `features.py`'s `spend` column makes it a
groupby. Scope throughout is own moves, `fullmove > 12`, non-mate,
`0 <= spend <= 60` (8 negative and 55 over-60 rows are clock adjustments and
lag, dropped exactly as `clockstate.py` does it).

**Blunder rate rises monotonically with think time, in both formats.**

| spend | 3+2 | 5+0 |
|---|---|---|
| 0 (premove) | 6.13% | 9.09% |
| 0–1s | 7.19% | 6.07% |
| 1–2s | 7.81% | 6.56% |
| 2–4s | 8.78% | 7.98% |
| 4–8s | 10.13% | 9.23% |
| 8–16s | 12.55% | 10.74% |
| 16s+ | 15.69% | 17.36% |

It survives conditioning. Direct standardization across 594 strata — move band
× legal-move quartile × captures available × eval bucket × in-check × format —
puts fast (≤2s) at 7.29% and slow (≥8s) at 12.78%, a +5.50 pp gap against
+5.77 pp raw. The difficulty proxies absorb almost nothing. Stratified
permutation, 2,000 shuffles: p < 0.0005.

### The predicted pattern is absent

The hypothesis worth testing was "fast move with plenty of clock → board vision
or impulse failure." That cell is the *safest* on the board:

| 3+2 | fast (≤2s) | slow (≥8s) |
|---|---|---|
| pressure (<30s) | 10.22% (n=11,653) | 16.92% (n=1,773) |
| moderate | 6.52% (n=9,685) | 13.63% (n=8,721) |
| comfortable (>90s) | 5.56% (n=11,686) | 12.44% (n=13,013) |

Time pressure is real and roughly additive, but it is the smaller of the two
effects. 5+0 shows the same layout.

### It reaches group P

Per eligible winning-middlegame move, floored hang rate by spend: 1.57% (≤1s),
2.96%, 4.01%, 4.31%, 5.35%, **8.18%** (16s+). Median spend on a floored hit is
8.0s against 6.0s across eligible moves. **Only 10% of floored hits occur on
moves of ≤2s.**

Holding the objective situation fixed — the 5,119 eligible positions where
material was *already* hanging before the move, so the task is identical
across rows — the failure rate still climbs:

| spend | failed to address a standing threat |
|---|---|
| ≤2s | 6.8% [5.13, 8.40] (n=917) |
| 2–4s | 10.4% [8.43, 12.32] |
| 4–8s | 11.5% [9.83, 13.33] |
| 8–16s | 13.4% [11.50, 15.31] |
| 16s+ | 21.4% [18.28, 24.37] (n=673) |

Self-inflicted hangs show the same gradient on a smaller base: 0.91% → 2.31%.

### What this does and does not license

**It does not license moving faster.** Think time is a *response* to difficulty,
not an independent input, and difficulty is not measured here — `n_legal` and
capture counts are weak proxies, and even the conditioned set above spans a
loose knight and a piece that cannot cleanly be saved. Reverse causality is the
leading explanation and this design cannot rule it out. Any reading of the form
"spend less time and blunder less" is unsupported and would be acted on at real
cost.

What holds regardless of causality is a **targeting** fact: the error mass sits
in positions that got real time. The plausible reframe is that hard positions
are correctly identified and then failed at two to three times base rate, which
is a resolution problem rather than a scanning one. That is consistent with the
~76% of blunders in won positions that are judgment rather than hanging
material, and it puts a question mark over the 15-second-scan drill protocol —
that format trains the ≤2s slice, which is 10% of the hits.

### The multi-PV test: solution narrowness does not explain it

`multipv.py` annotated the full contrast set — all 3,076 conditioned positions
with a usable clock at ≤2s or ≥8s — at depth 16, `multipv 8`, recording how many
moves come within 100cp of best. Coarse bins: only-move (1) / narrow (2–3) /
wide (4+).

**The selection runs backwards from the confound hypothesis.** Fast moves sit
on positions with *fewer* adequate replies, not more:

| | only move | narrow (2–3) | wide (4+) |
|---|---|---|---|
| fast (≤2s) | 51.0% | 29.7% | 19.3% |
| slow (≥8s) | 31.4% | 33.8% | 34.9% |

Failure to address a standing threat, within difficulty bin:

| difficulty | fast (≤2s) | slow (≥8s) | gap |
|---|---|---|---|
| only move | 6.6% [4.5, 9.0] n=468 | 19.5% [16.4, 22.5] n=677 | +12.9 |
| narrow (2–3) | 7.7% [4.8, 11.0] n=272 | 15.4% [12.8, 18.1] n=729 | +7.6 |
| wide (4+) | 5.6% [2.3, 9.0] n=177 | 12.9% [10.5, 15.4] n=753 | +7.2 |

Standardized across the three bins: fast **6.7%**, slow **16.2%**, gap
**+9.5 pp** — conditioning does not attenuate the raw gap at all.

### The difficulty interaction did not replicate

On the first 1,300 positions the gap ordered monotonically by difficulty
(+12.2 / +9.7 / +4.9 pp), which fits an appealing mechanism: see it and play it
fast, or fail to see it and grind. The only-move-minus-wide contrast was
+7.3 pp at p = 0.052, so the remaining 1,776 positions were annotated to settle
it.

**On the held-out 1,776 alone the interaction is +0.2 pp, p = 0.47.** The
monotone ordering is gone — held-out gaps run +13.1 / +6.9 / +12.9. The
pooled 3,076 figure of +5.6 pp at p = 0.027 is not a valid test, because the
1,300 in which the pattern was spotted are inside it.

Third instance of this failure mode here, after the June 2025 dip and the
Q1→Q3 hanging-material drop. All three: a monotone ordering across small bins,
a mechanism that explains it, and no replication. **Do not re-chase it.** The
honest reading is that the fast/slow gap is roughly constant across solution
narrowness.

The main effect is unaffected — it rests on 3,076 positions and a standardized
+9.5 pp, not on the ordering.

**What this closes and what it doesn't.** The natural confound — that long
thinks select positions where only one move works — is refuted, and refuted in
the wrong direction to rescue it. Solution narrowness does not explain the
think-time gradient.

But `n_within_100` measures how *narrow* a solution is, not how *hard it is to
find*, and here those come apart badly. When material is hanging and exactly one
move holds, that move is frequently forced and obvious — a recapture, the single
escape square — so it is played in two seconds and counted as maximally
difficult. That is the likeliest reading of the 51.2% figure above, and it means
this instrument is measuring something adjacent to what the question needs.

So: one door closed, not all of them. Human difficulty remains unmeasured, and
a design that captured it — reply-move complexity, whether the saving move is a
capture or a quiet retreat, whether the threat is one or two moves deep — would
be a different annotation, not more depth on this one.

The finding stands as a targeting fact and is now harder to explain away. It
still does not license moving faster; see the paragraph above.

### The annotations are committed

`multipv.py` output for all 3,076 conditioned positions is stored at
`chess/data/multipv_standing_threat_d16.jsonl.gz` — depth 16, `multipv 8`,
178 saturated. Unlike the `features.py` tables, which regenerate in 100 s and
are gitignored, this is ~75 minutes of engine time and does not come back
cheaply. Use it rather than re-running:

```bash
gunzip -c chess/data/multipv_standing_threat_d16.jsonl.gz > mpv.jsonl
```

`multipv.py` resumes by `(gid, ply)`, so pointing it at this file as its output
and passing a wider `--keys` extends the set rather than redoing it.

`multipv_first_subsample_seed23.csv` records which 1,300 positions were
analyzed *first*. The held-out replication below depends on that split, and
regenerating it from the seed alone is fragile — it assumes the row order of an
intermediate file. Keep the list.

### A resumability trap worth remembering

`fens.csv.gz` is ordered by block, so a budgeted `multipv.py` run left partway
through holds an all-2024-H2 sample. The first 171 positions computed here were
exactly that. Analyzing a partial file would have produced a single-block result
presented as corpus-wide, with nothing visibly wrong with it.

Any resumable runner over a sorted input has this property. Draw a seeded
random subset up front and run *that* to completion, rather than truncating a
sorted queue — the same reasoning as the rarefaction and block-selection
artifacts recorded elsewhere in this README.

## What the opponent's previous move predicts

The raw crosstab said forcing moves are followed by *fewer* blunders than quiet
ones — checks 7.95%, captures 8.46%, quiet 10.16% — which is backwards from the
intuition and was sitting in the open threads as an uncontrolled result.

All three rows are confounded, each in a different way. `oppmove.py` reports the
controlled version:

```bash
python3 chess/scripts/oppmove.py /home/claude/features/moves.csv.gz
```

It hard-exits if the raw crosstab does not reproduce the four published rates,
on the `features.py` precedent — validate against a known number before
trusting a new pipeline.

Scope: own moves, `fullmove > 12`, non-mate, 108,151 rows. Blunder =
`drop_cp >= 200`, at the +2 line and inside the depth-12 reliable band. Method
is the think-time treatment — direct standardization across move band ×
`n_legal` quartile × `n_caps_avail` × eval bucket × `tc`, within-stratum
permutation for p, game-clustered bootstrap for the interval. Row-level
intervals would be too tight; moves inside one game share an opponent, a clock
trajectory and a position.

**`in_check` is not a stratum axis here, unlike the think-time run.** It is
perfectly collinear with the exposure for the check arm — 0 disagreements in
108,151 rows — so including it leaves zero usable strata rather than
controlling anything.

### The capture effect is a recapture effect

| group | n | raw | standardized |
|---|---|---|---|
| quiet | 68,774 | 10.16% | 9.96% |
| capture — recapture | 14,689 | 7.31% | **7.92%** |
| capture — fresh | 12,691 | 9.79% | **10.72%** |
| pawn_break | 2,462 | 10.44% | 10.24% |

- quiet − recapture: **+2.02 pp** [+1.43, +2.66], p < 0.002
- quiet − fresh capture: **−0.80 pp** [−1.44, −0.15], p = 0.024
- pawn_break − quiet: +0.15 pp [−1.39, +2.57], p = 0.91

The pooled capture row was two populations glued together. When the opponent
takes something you can take straight back, the reply is close to automatic and
the blunder rate is genuinely low. When the opponent takes something fresh, the
rate is *above* quiet, not below. Splitting on `opp_prev_was_recapture` — a
column `features.py` already carries — resolves the paradox entirely and
reverses the sign of the part that was interesting.

The surviving pooled contrast (quiet − capture, +1.03 pp [+0.55, +1.50]) is
therefore not worth quoting on its own. It is a weighted average of a large
real effect and a small opposite one.

`pawn_break` is null against quiet and stays null. On 2,462 rows the interval is
four points wide, so this is "not detected," not "not there."

### The check row is not identifiable

Not a null result — an unanswerable one, and worth recording as such rather
than as an effect size.

`in_check` is collinear with the exposure, and `n_legal` barely overlaps:
median 3 legal moves after a check against 31 otherwise. Only 4,002 non-check
rows have `n_legal <= 8` at all, against 9,522 check rows.

Forcing the comparison into that overlap, exact-matched on `n_legal`, gives
check −2.00 pp [−3.70, +0.15], p = 0.13 on 8,464 rows. Directionally safer,
interval covers zero, and the comparison group — non-check positions with under
nine legal moves — is itself unusual enough that a clean read was never
available. **The published 7.95% is measuring the difficulty of picking the
wrong move out of three, not anything about checks.**

### Old threats are the dangerous ones

The raw created-threat row is definitional. `opp_created_threat == 1` implies
`see_standing >= 150` in every one of 19,486 rows — 0 exceptions — so half the
raw comparison is positions where nothing can be hung, which guarantees a low
rate for reasons unrelated to skill.

Re-posed within the material-hanging set, where the arms are comparable, it
**reverses**:

| | n | raw | standardized |
|---|---|---|---|
| threat newly created | 19,486 | 11.58% | 11.46% |
| threat already standing | 3,006 | 16.73% | **17.74%** |

**−6.28 pp [−7.88, −4.70], p < 0.002**, over 4,631 games.

The threat the opponent just created gets handled. The threat that has been
sitting there — that already survived one of your own moves — is the one that
costs material. Fresh danger draws a re-scan; a threat that persists through a
quiet continuation becomes furniture.

This agrees with the think-time section's standing-threat gradient rather than
competing with it, and it sharpens the group P protocol: the reflex to train is
not "look harder after a forcing move," it is "re-check the threats that were
already on the board before this move."

**The selection caveat is load-bearing.** For a threat to be "already
standing," it must have survived a previous own move, so that arm is selected
on having already been missed once. Some unknown share of the 17.74% is that
selection rather than a fact about stale threats. This design cannot separate
them — same shape as the reverse-causality caveat on think time, and it should
be read with the same restraint. What holds regardless is the targeting fact:
the error mass sits on threats that are not new.

### What this closes

Open thread 1 is resolved. Two of its three rows were artifacts of how the
exposure was defined rather than findings about forcing moves, and the third
is a real effect pointing the opposite way from the raw table. The general
lesson is the one the `material.py` benchmark section already records in a
different form: **check what a category guarantees before comparing rates
across it.** `opp_created_threat` guaranteed the outcome was possible;
`capture` guaranteed nothing consistent at all.

## The first major deterioration: level games are decided early

Thread 2, run Aug 2026. The question: in games entered level, is there a
*moment* where the thread is lost — and does it sit in the npm 19–13 band where
`material.py` located the level-position deficit?

```bash
python3 chess/scripts/firstdrop.py /home/claude/features
```

Validation-gated on the features.py precedent: it hard-exits unless the input
is the 5,404-game / 178,684-row run, the published bucket counts reproduce, and
the middlegame-entry buckets below reproduce. Every number in this section
prints from that one command.

### Middlegame entry has a POV trap

Entry eval must be measured **side-aware** — White: `cp_before` of own move 13;
Black: `cp_after` of own move 12. Reading `cp_before` of the first own move
≥ 13 for both colours measures the position *after the opponent's move* when
playing Black, and opponent errors systematically inflate that eval: it moved
~280 games from `level` into `up` before the fix. The side-aware own-move proxy
recovers the phase map's every-ply buckets to within 0.5–2%:
**4,600 games = 1,662 up / 1,930 level / 1,008 down** against the phase map's
4,637 = 1,670 / 1,938 / 1,029 (the 37-game gap is games with no own move at
the entry ply). Same family as the endgame-entry ply bug — one ply of POV
drift is enough to corrupt a bucket table while looking plausible.

### Fate of the first drop decides the game

First drop = first own move with `drop_cp >= 200`, non-mate. Recovered =
`cp_after` back within 50cp of the pre-drop eval within 5 own moves. Level
games, n = 1,930:

| first-drop fate | n | score |
|---|---|---|
| no 200cp drop ever | 305 | 80.3% |
| dropped, recovered | 545 | 58.2% |
| dropped, permanent | 1,080 | 28.8% |

The gradient is partly definitional — losing games contain drops — so do not
quote it as a finding on its own. What is not definitional: **56% of level
games contain a permanent drop, and that share is 55–57% in every one of the
seven blocks**, both chess.com blocks included. Same replication shape as the
hanging-material result. Median timing: **fullmove 16**, IQR 13–22. 59% of
permanent first drops land in **moves 13–25 with npm ≥ 13** — the hot zone —
and that share is 56–60% across every threshold (200/300) and recovery window
(3/5/8) tested.

### The npm 19–13 prediction: half right, wrong lens

The marginal distribution does peak at npm 19–13 (hazard 8.4 per 100 at-risk
moves vs 3.5 at 24–20). But the cross-tab reverses it. First-drop hazard per
100 at-risk own moves, level games:

| npm \ moves | 1–12 | 13–18 | 19–25 | 26+ |
|---|---|---|---|---|
| 24–20 | 1.65 | **9.87** | **12.01** | (n=22) |
| 19–13 | 3.85 | 6.14 | 10.09 | 11.33 |
| 12–8 | — | 5.76 | 7.14 | 7.05 |
| 7–0 | — | — | 7.14 | 5.33 |

**Conditional on move number, hazard is highest at full material and falls
monotonically as pieces come off** — the opposite ordering from the prediction.
The marginal 19–13 peak is composition: that band happens to span the dangerous
moves. So there *is* a moment, and it is the early middlegame — but the
dangerous state is piece-heavy positions at moves 13–25, not a material band.

This also closes the loop on `material.py`. A game still level at an npm 19
crossing is at ~move 15 with the whole hot zone ahead of it; a game still level
at npm 11 has already survived it. The crossing deficit that peaked at npm
19–13 and vanished by 11 was the hot zone seen through a material lens —
selection, not a property of those material levels.

### The mechanism: judgment on considered moves in quiet positions

The 633 permanent hot-zone first drops:

| | hot zone | baseline (all such moves) |
|---|---|---|
| hang_label `none` | **70%** (442) | — |
| material already hanging (SEE ≥ 150) | 29% | 26% |
| opponent had just created a threat | 27% | 22% |
| opponent's previous move quiet | **71%** | — |
| spend, median | **8.0s** | 6.0s |
| played in ≤2s | 13% | — |
| in check | 2% | — |

The move that decides a level game is typically a *considered* move — more
time than baseline, only 13% snap moves — in a quiet, piece-heavy position
with nothing hanging and no fresh threat. A judgment failure after real
thought. That is the think-time targeting fact localised: the error mass was
already known to sit on moves that got real time; now it has an address —
the early middlegame of level games. Standing threats are barely elevated
(29% vs 26%), so this is *not* the group P phenomenon wearing a disguise;
group P's ~24% ceiling is confirmed from yet another direction.

### What it does not say

Where and what kind, not *why*. Distinguishing "bad plan" from "missed a
tactic two moves deep" needs eyes on positions — thread 6's
difficulty-instrument gap, which no groupby closes. Group R below exists to
collect exactly that evidence. And the usual causal caution: spend at the drop
is a response to the position; nothing here licenses moving faster.

### Group R: the reflection set

`build_reflect.py` puts the top 40 of these positions (by win-probability
cost, Lichess blocks only, matching group P's Lichess-only precedent) on the
drill page as **group R** — not a drill but a notebook. Each card shows the
position before the move, the opponent's quiet previous move, the move played
and the time spent, then a free-text box: *why this move — what did you see,
what was the plan, what were you worried about?* The spoiler holds the eval
swing and a depth-16 "what was better" line (deeper than the corpus on
purpose; these ~40 engine lines cache in `features/reflect_engine.json`).

Selection: level at entry, permanent first drop, moves 13–25, npm ≥ 13,
`hang_label == none`, quiet opponent move, not in check — the hot-zone
judgment set, 274 candidates, top 40 taken.

Notes persist in `localStorage` under `drills.reflect.v1`, keyed
`R-{gid}-{ply}` on the stable-id precedent, so rebuilds keep notes attached to
their positions. The **Copy my notes as JSON** button exports every non-empty
note *with its position context* (FEN, move played, evals, spend) — the
intended workflow is to write a batch, export, and read them back in a session
to look for what is systematically seen and missed. Reflection cards carry no
`class="drill"` and no tick checkbox, so the 260-drill counter and the reset
button never touch them; running `build_reflect.py` twice is byte-identical,
and it does not disturb the P/A/B/C/D blocks.

```bash
python3 chess/scripts/firstdrop.py /home/claude/features    # selection input
python3 chess/scripts/build_reflect.py                      # -> chess-drills/index.html
```

### The forcing layer: not what I miss, what I let happen

The first nine group R notes produced a hypothesis, and seven of the nine
contained some version of "I never saw that capture." Tested with
`forcingtest.py`:

```bash
python3 chess/scripts/forcingtest.py /home/claude/features --depth16-check
```

Treatment = the 330 permanent hot-zone judgment drops (both sites). Control =
positions passing the *same* filters from the *same* games where the move
played was fine (`|drop_cp| <= 30`), one per game, n matched. Controls differ
from treatment in the outcome only — not phase, material, opponent-move type
or check state. Two depth-12 searches per position; forcing = capture or
check; permutation on the group label, 10,000 draws.

The hypothesis is ambiguous between two claims, and they come apart:

| depth 12, n = 330 each | blunders | controls | Δ | p |
|---|---|---|---|---|
| **H1** best move in the position is forcing | 28% | 28% | −0.6 pp | 0.93 |
| **H2** best *reply* to the move played is forcing | **57%** | 27% | +29.4 pp | <0.0001 |
| the move actually played was forcing | 18% | 32% | −14.5 pp | <0.0001 |

**H1 is null.** Blunder positions contain no more missed resources than
positions played fine. And in controls where the best move *was* a capture or
check, he played it **87%** of the time, against 48% when the best move was
quiet. Finding his own forcing moves is a strength, not a weakness — the vivid
"I never saw the hanging queen" moments in the R notes occur at base rate and
are a hindsight artefact.

**H2 is large.** The game-deciding move is a *quiet* move that loses to an
*immediate* capture or check. Depth-16 replication on a 60/60 subsample holds
both halves: 23%/33% on H1, 53%/27% on H2.

Caveat, stated because the number invites over-reading: a ≥200cp drop usually
has to cash out as material, so part of H2's 57% is mechanical. The finding is
the **asymmetry**, not the level — own forcing layer handled at 87%, the
opponent's not checked at all. Do not quote the 57% alone.

This unifies three previously separate results, all of which are
opponent-resource blindness and none of which is own-resource blindness:
standing threats reading 6.3 pp more dangerous than fresh ones, group P's
`missed_their_threat` class, and H2. **The unification is descriptive, not a
claim that they are one event** — see "Three failure modes, not one" below,
where they turn out to be close to statistically independent. The training rule
that follows is one-sided and cheap: **move chosen, hand not yet moved — what are their checks
and captures against the position this creates?** That layer accounts for 57%
of these errors. The other 43% get punished quietly and no scan will catch
them; they are what the rest of the R notes are for.

The mechanism, as he described it unprompted in a group R note (game
`vQvOtLkI`, 15...Qg6) before any of this was analysed:

> I am scanning these positions and seeing no immediate threats or one threat,
> so I assume I can just play the move to respond to the one threat or play the
> plan I had in mind already.

That is H2 stated from the inside: the scan runs on the position *as it stands*,
finds nothing or one thing, and never runs again on the position the chosen move
would create. Worth keeping verbatim — it is the clearest statement of the
failure in the project, and it came from the player, not the tables.

Two documented members of the quiet-punishment 43%, for whoever picks this up:
`7k30XvzG` 21...Qb8 and the queen trap after `vQvOtLkI` 15...Qg6 (16.Bc2). Both
are positional and neither is caught by any forcing-move check.

### All 40 group R notes: what the batch says

Completed Aug 2026. The first nine generated the forcing-layer hypothesis; the
remaining 31 were written afterwards and the full batch exported as JSON. What
follows is a **qualitative reading of 40 self-reports**, and it must not be
read as evidence at the level of anything else in this README. Three reasons,
all of which the batch itself demonstrates:

- **n = 40**, selected as the *costliest* hot-zone judgment drops, so it is the
  tail of the distribution, not a sample of it.
- **Hindsight contamination.** Every note was written with the position on
  screen and the spoiler one click away. Several notes visibly change direction
  mid-paragraph once the answer is checked.
- **Introspective salience is not frequency.** Already established the hard way
  in this project; the batch supplies a second demonstration, below.

Use these as a hypothesis source and a description of the phenomenology. Every
claim here needs a matched-control test before it counts.

#### 1. The deficit is the trigger, not the vision

The most consistent thing in the batch: **when the card forces a look, the look
usually works.** Across roughly a dozen notes he correctly predicts the answer
before opening the spoiler — `cA2oTuZe` ("before checking the answer, I now see
the knight fork on c6" — yes), `ODQTL7Lp`, `T1BHxakK`, `bFQvzzSM`, `zrOBgtud`,
`2SVfN1tw`, `SXNKVcS7`. Stated directly in `vQvOtLkI`:

> that's hard for me to see and I would only find it by knowing something was
> there.

This is the most decision-relevant thing in the batch, because it discriminates
between two remedies. If the failure were *capacity* — can't see these patterns
— the answer would be pattern training at volume. If it is *invocation* — the
scan is competent but doesn't fire — the answer is a cheap unconditional
trigger, which is exactly the H2 pre-move check the forcing-layer section
already recommends. The batch leans hard toward invocation.

Caveat that has to travel with it: predicting the answer *given* that a card
says an error occurred here is a far easier task than finding it at the board
under a 3+2 clock with no such guarantee. This is suggestive of invocation, not
proof of it.

#### 2. H2 restated from the inside, repeatedly

The `vQvOtLkI` quote above was one note. The full batch says the same thing in
many voices: "I definitely didn't look at Black's responses" (`1mylWNui`),
"never considered that my opponent could move its bishop and grab my queen"
(`Tjx1Tbg9`), "didn't check on what the response might be" (`ZRgDesop`), "I
just didn't sense any clear danger" (`uq7BvP6Y`).

One sub-pattern is worth naming because it is mechanically specific and easy to
drill: **moves that change the geometry, scanned on the old geometry.** Pawn
moves dominate it — `3eLsCWEU` (17.f3 weakens e3, and he says so: "I didn't see
how I weakened e3 with my move"), `SXNKVcS7` (14.f4 opens Nxe3 forking queen and
rook), `KcwgSovn` (21.g4 and the queen ends up trapped). A committal pawn move
is precisely the case where the position after the move is *least* like the
position scanned, which is a plausible reason this class is over-represented —
but "over-represented" here is 3–5 notes out of 40. **It has now been tested
against the corpus and it is null** — see "Pawn moves are not more dangerous
than piece moves" below.

*Correction.* An earlier revision of this paragraph said `features.py` "already
carries the move played." It does not: `moves.csv.gz` carries `opp_prev_san`,
the *opponent's* previous move, and there is no column for the player's own
SAN. `pawnpiece.py` re-walks the annotated PGNs to recover it and merges on
`(gid, ply)`. The claim was wrong when written and is corrected here rather
than quietly deleted, on the same principle as the retracted-findings section.

#### 3. The H1 illusion is stronger in the full batch, and is still null

**About 12 of the 40 notes — roughly 30% — center on a missed opportunity of
his own** rather than a missed threat: a hanging enemy queen (`3ZLHVBRE`), a
free rook (`7DITZaKI`), a loose piece (`PjDjVZR9`, `cMp7o2xx`), an unplayed
fork (`P6CmgTjR`), a resource never considered (`f7Y2RfNx` "I certainly never
considered Rb4", `x1r5LfF9` "never considered or saw Rxh2", `uq7BvP6Y`,
`wX0eYRY3`, `nx39s6Dw`, `MXQW6nTb`, `cA2oTuZe`).

Two of them explicitly notice the mismatch and say so — `PjDjVZR9` ("this
doesn't seem to fit the others"), `cMp7o2xx` ("again, not a missed threat to me
but a missed opportunity").

**This is the single most important thing in the batch, and it is important as
a warning.** Thirty percent is a large, vivid, self-consistent pattern that the
player independently identified as a distinct category. It is also the exact
claim `forcingtest.py` tested against matched controls and found **null at
p = 0.93** — blunder positions contain no more available captures and checks
than positions from the same games where the move played was fine, and where
the best move *was* forcing he played it 87% of the time.

Nothing here reopens H1. What the batch adds is a measured sense of how
misleading introspection is on this axis: the null hypothesis produced a 30%
subjective hit rate in the tail. Anyone reading these notes fresh will
reconstruct H1 within ten cards. It is on the do-not-re-chase list, and this
section is the reason it will keep looking worth re-chasing.

#### 4. Planlessness precedes the committal quiet move

A recurring setup, roughly 6–8 notes: no candidate appealed, so a default move
got played. "I suspect I scanned the options my pieces had and didn't see
anything compelling so I pushed a pawn" (`cA2oTuZe`); "not sure the plan other
than a vague idea to park a rook on the semi open file" (`7DITZaKI`); "I didn't
have a concrete plan, but thought I could create some kind of problem by
pushing the king around enough" (`2QMMesgU`); "I don't think I had much of a
plan after that" (`wX0eYRY3`).

**This is the best qualitative candidate yet for the positional-decay
residual** — the 32% of hot-zone drops that `pvplayout.py` found never become
material at all, and the 57% positional share above +350cp. It fits the shape:
a considered move (median 8s), quiet, nothing hanging, no forcing punishment,
eval simply stops being his. Two of the notes are from positions he was already
winning, which is where that regime lives.

It is also the hardest thing here to turn into a test, because "had no plan" is
not a column and has no obvious proxy. Do not start by running an engine; this
is the thread 6 design problem wearing different clothes.

#### 5. Four notes where review did not resolve the error

`7k30XvzG` ("even now, I don't see the danger in my move... there's something
I'm missing here"), `2QMMesgU`, `f7Y2RfNx` in part, and `3ZLHVBRE` ("no idea
what I was thinking here"). These are positions where the player had unlimited
time, the answer available, and still could not reconstruct what went wrong.

Worth keeping as a category. A hot-zone drop that survives untimed review by
the person who played it is not a scanning failure under any reading, and these
are the most likely members of the positional bucket. `7k30XvzG` was already
recorded above as a documented member of the quiet-punishment 43%, from the
first nine notes, which is mild independent support for the category.

#### 6. Player-flagged eval errors: three claimed, one real

Three notes dispute the engine: `bdWcvWUA` (13.Bf3), `Ifg6B0mx` ("this looks
like another eval error. Lichess doesn't see this as +6"), and `qwOlV23r` (the
spoiler's reply line). `bdWcvWUA` is the confirmed corrupt eval already
documented under "Individual evals can also just be wrong" — and note it was
found *by reading a group R card*, which is how it entered this README in the
first place. The other two are unverified.

**Do not read this as a 7.5% error rate.** The measured rate of gross eval
corruption is ~0.3% (one position in 330, re-evaluated at depth 12/16/20), and
`Ifg6B0mx` at `cp_before` = 602 sits above the +5 line where depth 12 is known
to be noisy — ordinary depth wobble is the null explanation and it has not been
ruled out. Player disagreement is a useful pointer and a bad estimator. If any
future analysis turns on these specific plies, re-check them against a live
engine first; nothing currently does.

#### 7. One concrete repertoire item

`owWTo8kf` 13.Ne5, met by Nxc6: "this has gotten me before in the London."
That is a named, recurring, fixable line rather than a statistical tendency,
and it belongs with the openings section's "where the book stops" table rather
than with any of the above. It is the only note in the batch that names a
specific opening trap.

#### What the batch does not support

Several notes self-diagnose as moving too fast (`6GWSiBPt`, "this one was just
me moving too fast"), and the batch does contain fast, costly errors. **That
question is closed** — thread 7 pre-specified a decision rule, both tests
failed (T1 non-monotone, T2 null at p = 0.31), and the surviving lean is logged
as a post-hoc flag. The notes are the source of that hypothesis, not evidence
for it, and re-reading them will make it feel true again.

#### Handoff

The exported JSON is the batch as written. The two testable hypotheses it
raises are **pawn moves versus piece moves** (§2, a groupby on existing
columns, needs a pre-specified rule and a held-out check given how many
post-hoc tests this corpus has already absorbed) and **planlessness** (§4, not
currently measurable). Everything else in this section is description.

### Pawn moves are not more dangerous than piece moves

The one testable hypothesis the 40 R notes produced. **Pre-specified in
`chess/scripts/pawnpiece_prespec.md`, written before any output was
inspected.** Result: **null**.

```bash
python3 chess/scripts/pawnpiece.py /home/claude/features7 \
  2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn \
  2026=corpus.pgn CC-2024Q4=cc_2024q4_analyzed.pgn \
  CC-2026=cc_2026febapr_analyzed.pgn
```

Scope is the **seven-block** run (5,404 games / 178,684 rows), matching the
`oppmove.py` precedent whose method this copies. Own moves, `fullmove > 12`,
non-mate, 108,151 rows. Blunder = `drop_cp >= 200`.

Four hard gates, all pass: the features run identity; the in-scope row count
of 108,151; **`oppmove.py`'s published raw crosstab reproducing exactly**
(check 7.95%, capture 8.46%, pawn_break 10.44%, quiet 10.16%) from columns this
analysis does not otherwise use; and 100.00% SAN merge coverage.

Castling is excluded as pre-specified — 1,602 rows, 1.48%, blunder rate 6.80%,
notably safer than either arm and structurally unlike both.

| | pawn | piece | diff |
|---|---|---|---|
| raw | 9.44% (n=22,501) | 9.61% (n=84,048) | **−0.17 pp** |
| standardized | **9.94%** | **9.55%** | **+0.40 pp** |

Standardization is across 390 strata — move band × `n_legal` quartile × eval
bucket × `in_check` × `tc` × **own move was a capture** — retaining 99.7% of
rows. Within-stratum permutation, 10,000 draws, seed 23: **p = 0.12**. The
pre-specified rule required p < 0.01. Null.

**The sign flip is the interesting part and is not a finding about pawns.**
Raw, pawn moves look *safer*; standardized, they look marginally worse. That
means pawn moves are selected into easier positions — which is a fact about
when he pushes pawns, not about pawn moves being dangerous. It is the same
lesson as the `material.py` benchmark section and the `opp_created_threat` row:
**check what a category selects for before comparing rates across it.** Without
the controls this would have been published as "pawn moves are safer," which is
equally wrong in the other direction.

What survives is +0.40 pp on a ~9.5% base — under a twentieth of the effect
size, and not distinguishable from zero at this sample size, which is 106,237
rows and not going to get meaningfully bigger.

The exploratory hot-zone cut (moves 13–25, `npm_light >= 13`, 41,896 rows), the
cut with the most overlap with the positions that generated the hypothesis, is
smaller still: raw −0.18 pp, standardized **+0.11 pp**. Labelled exploratory in
the pre-spec and it does not rescue anything.

**Fifth notes-derived hypothesis to test null or reverse**, after H1, the June
2025 dip, the difficulty interaction and thread 7. That base rate was written
into the pre-spec as the prior and is now worth treating as a standing
expectation rather than a repeated surprise: the R notes are an excellent
source of *mechanism description* and a poor source of *frequency claims*. The
one place a note has changed a published finding remains `bdWcvWUA`, where the
player caught a corrupt eval — an observation about a single position, not a
rate.

### Three failure modes, not one

The forcing-layer section groups the standing-threat result, group P and H2
under one description. The obvious next question is whether the description is
hiding a single underlying event — whether the standing-threat finding and the
thread 2 first-deterioration finding are the same thing seen from two angles.

```bash
python3 chess/scripts/firstdrop.py /home/claude/features   # produces the input
python3 chess/scripts/coincide.py  /home/claude/features
```

Validation-gated on the `firstdrop.py` precedent: it hard-exits unless the input
is the 5,404-game / 178,684-row seven-block run and the published event counts —
standing arms 19,486 / 3,006 at 16.73%, 1,930 level-entry games, 633 hot-zone
drops — all reproduce. Every number below prints from that one command.

Events, all defined from columns already in `moves.csv.gz`:

- **A** — permanent hot-zone first drop, in a game level at middlegame entry
  (633 games)
- **B** — standing-threat blunder: own move, `fullmove > 12`, non-mate,
  `see_standing >= 150`, `opp_created_threat == 0`, `drop_cp >= 200` — the
  failed half of the "already standing" arm (503 moves in 420 games)
- **P** — group P floored `missed_their_threat` hit (629 moves in 522 games)

**Answer: they are not the same event, and they are close to independent.**

#### They are almost never the same move

Only **14 of the 633** hot-zone drops (2.2%) are also standing-threat blunders;
28 (4.4%) are group P floored hits. The decomposition shows why, and it is more
informative than the 29%-vs-26% figure the thread 2 section reports:

| of the 633 hot-zone drops | n |
|---|---|
| no material hanging | 451 (71%) |
| hanging, threat the opponent **just created** | 168 |
| hanging, threat **already standing** | **14** |

The hanging-material minority of the hot zone is almost entirely *fresh*
threats — the arm `oppmove.py` found to be the **safe** one. The stale-threat
mechanism is essentially absent from the hot zone. The "barely elevated
(29% vs 26%)" line in thread 2 was right about the conclusion and was averaging
over two arms that point opposite ways.

#### They barely co-occur in the same games

Within the 1,930 level-entry games, exposure-matched on own moves after move 12
(quintiles) so that long games cannot fake co-occurrence, 10,000 within-stratum
permutations, seed 23:

| | both | observed | independence predicts | odds ratio | p |
|---|---|---|---|---|---|
| A × B | 71 | 3.7% | 3.2% | 1.30 [0.95, 1.75] | 0.12 |
| A × P | 63 | 3.3% | 2.9% | 1.19 [0.85, 1.62] | 0.21 |

A slight positive lean, neither significant, both intervals covering 1.0. Two
tests run, both null.

#### The before/after cut is definitional — do not quote it

Of the 86 standing-threat blunders inside the 71 co-occurring games: 72 after
the first drop, 14 at it, **0 before**. That zero is forced — a standing-threat
blunder is by definition a ≥200cp drop, and the first drop is the *first* ≥200cp
drop, so nothing can precede it. Same family as the `opp_created_threat` row
being definitional: check what a category guarantees before comparing across it.
What is informative is that most standing-threat blunders in these games land
*after* the game was already decided.

#### The loss budgets add rather than overlap

| within the 1,930 level-entry games | games | losses | % of 1,016 | score |
|---|---|---|---|---|
| A only | 562 | 397 | 39.1% | 27.4% |
| B only | 115 | 68 | 6.7% | 38.7% |
| **both** | **71** | **54** | **5.3%** | 22.5% |
| A or B | 748 | 519 | 51.1% | 28.7% |
| A or B or P | 827 | 559 | 55.0% | 30.5% |

Corpus-wide over 5,404 games and 2,585 losses: A or B is **26.2%** of all
losses, A or B or P is **32.4%**.

The marginal-effect check is the sharpest evidence they are distinct. In games
with no hot-zone drop, a standing-threat blunder costs 55.8% → 38.7%
(−17.1 pp). In games that already have one, it costs 27.4% → 22.5% (−4.9 pp).
If these were one event, B would add nothing once A had happened. It adds less,
not nothing — the shape of a floor effect in games already lost.

#### What this changes

The opponent-resource-blindness umbrella stays as a *description*; it is not one
mechanism. Three consequences:

1. The H2 pre-move check and the standing-threat re-scan address **different
   games**, so their value adds rather than overlapping. The combined story
   covers ~32% of all losses, which is the number to quote rather than anything
   smaller derived from assumed overlap.
2. The hot zone is not group P wearing a disguise, confirmed a second way — 2.2%
   move-level overlap, and the material that does hang there is fresh, not stale.
3. Anything targeting stale threats will not move the thread 2 flow, and vice
   versa. They are separate training targets.

**Status and caveats.** Not pre-specified — the question came out of a summary
of open items, so read it as exploratory. Two co-occurrence tests were run and
both are null, which is the direction that needs least protection from multiple
comparisons. The standing-threat arm carries its usual selection caveat (a
threat is "standing" only if it survived a previous own move). And "games
containing the event" is an upper bound on attribution, not a causal share —
the 72 post-drop standing-threat blunders are mop-up in games already lost.

### Thread 7: does severity skew fast? No.

Several group R notes observed that some of the *costliest* drops were 1-3s
moves against a hot-zone median of 8s, suggesting severity and frequency run
opposite. Tested with the rule written down first:

```bash
python3 chess/scripts/thread7.py /home/claude/features
```

**Pre-specified decision rule:** mean `wp_error` must decline roughly
monotonically with spend (T1) AND the top `wp_error` decile must over-represent
<=2s moves against the 13% base rate (T2).

| spend | n | mean `wp_error` | 95% CI |
|---|---|---|---|
| <=2s | 83 | 0.302 | [0.274, 0.332] |
| 2-4s | 90 | 0.320 | [0.292, 0.348] |
| 4-8s | 148 | 0.289 | [0.272, 0.306] |
| 8-16s | 190 | 0.271 | [0.257, 0.287] |
| 16s+ | 119 | 0.279 | [0.261, 0.298] |

T1 is not monotone — 2-4s is the peak and 16s+ turns back up. T2 is null: 15.9%
of the top decile at <=2s against a 13.2% base, p = 0.31. **The rule fails.**

A directional lean survives and is worth logging, but only as a flag. Holding
sharpness fixed (`n_legal` tercile x `n_caps_avail` x eval bucket), fast is
+0.041 worse, permutation p = 0.008; median spend in the top decile is 6.0s vs
8.5s, p = 0.016; and the direction holds on all four splits tried (Lichess
+0.045, chess.com +0.019, 2024-25 +0.031, 2026 +0.079). **Both tests are
post-hoc** — added after the point estimates leaned — the fast arm is 83
positions and the chess.com arm is 8. This is the exact shape of the three
findings already retracted here: plausible mechanism, monotone-looking point
estimates, no pre-specification. Not promoted. Even if it later replicates,
the ceiling stands: it would identify a subset worth pausing on, not license
"move slower".

### Clock: the first cut that separates clock from difficulty

The standing caveat is that clock state at any crossing is downstream of the
middlegame that produced it, so nothing licenses moving faster. The way out:
a clock *advantage* has two sources, and they are not equally confounded. Your
own speed is tangled with your position's difficulty. The opponent's pace is
largely their trait.

```bash
python3 chess/scripts/clockdecomp.py /home/claude/features
```

**C1**, at fullmove 25 (3+2, n = 3,377), both axes carry weight: your clock
high-vs-low is +10.4 pp holding theirs fixed, theirs low-vs-high is +13.3 pp
holding yours fixed. Not decisive — pressing an opponent makes them slow, so
their move-25 clock is partly your doing.

**C2** is the real cut. Opponent pace measured over moves 1-12, before
middlegame difficulty diverges, standardized over your own opening pace and
opponent Elo quartile, 3+2 only (n = 4,433):

| opponent's opening pace | n | raw | standardized |
|---|---|---|---|
| slow | 1,491 | 52.6% | **53.6%** |
| mid | 1,521 | 48.3% | 48.2% |
| fast | 1,421 | 45.6% | **45.5%** |

**+8.1 pp, two-sided permutation p = 0.0003.**

**C3** kills the obvious alternative — that fast opponents are simply better
prepared. Eval at move 12 is flat across the three groups (median +19 / +11 /
+13 cp; share worse than -100 running 26.9 / 25.1 / 23.0%). Adding eval@12 to
the stratum set attenuates the contrast only to **+7.0 pp, p = 0.0003**, and it
is largest in the level bucket (51.8% vs 41.7%).

**What this licenses.** For the first time in this corpus, a clock edge shows
value that cannot be attributed to your own position's difficulty, because the
variation is in the opponent's behaviour rather than yours. What it does *not*
license is anything about your own speed: the mirror arm is non-monotone
(44.6 / 51.7 / 51.3 standardized), slow openings being worst for you is exactly
the confounded direction, and the think-time gradient is untouched by this.

Residual threat: opponent opening pace is not randomly assigned and may proxy
playing style rather than clock alone. Real, but far weaker than the objection
that has blocked every previous clock result. A difficulty instrument (thread 6)
would close it properly.

### The quiet-punishment 43%, characterized

H2 covers 57% of the 330 hot-zone judgment drops. The residual was defined only
by what it is not, and no forcing-move check will ever reach it.

```bash
python3 chess/scripts/forcingtest.py /home/claude/features   # prerequisite
python3 chess/scripts/quiet43.py     /home/claude/features
```

n = 143 quiet-punished vs 187 forcing-punished. Almost everything is null —
spend, `fullmove`, `npm_light`, `n_legal`, captures available, king attackers,
material balance, game length, score. One contrast is large and clean:

| | quiet-punished | forcing-punished | p |
|---|---|---|---|
| `cp_before` | **+210** | +116 | 0.0003 |
| `cp_after` | **-131** | -237 | 0.0001 |
| `drop_cp` | 341 | 353 | 0.43 |

Same size of error, different endpoints. The quiet half starts from a position
you had *already made good* and lands somewhere only slightly worse. The forcing
half starts near level and lands clearly lost. So quiet punishment is not a
cheaper error — it is an error made from a better position, and it is the one
where nothing hangs, nothing checks, and the eval simply stops being yours.

Three things that looked like findings and were killed:

- **Opponent Elo +93 in the quiet half.** Entirely chess.com pool calibration.
  Within Lichess: +12, p = 0.18.
- **The quiet half keeps bleeding** (-128 -> -335 vs -246 -> -366 over the next
  five own moves). Tested properly the difference is -35 cp at p = 0.27, and the
  forcing half starts lower so a floor effect is live. Do not quote the
  trajectory numbers.
- **Site difference in quiet share**, Lichess 48% vs chess.com 21%, p = 0.0002.
  Rests almost entirely on CC-2024Q4 (CC-2026 is n = 6), and the date-matched
  Sep-Dec 2024 contrast is +17.9 pp at **p = 0.14**. Logged, not promoted.

**Handoff.** The 143 positions are written worst-first to
`features/quiet43.csv`. The paid half — a depth-16 PV playout splitting *delayed
tactic* from *positional decay* — has since been run; see "Two regimes, split by
how good the position was" below. Answer: mostly positional, and sharply
dependent on the pre-move eval.

**Also note:** `cp_before` and `cp_after` are one fact, not two. `cp_after =
cp_before - drop_cp` exactly (zero residual across all 330 rows), and `drop_cp`
is null between the halves, so the two p-values above are the same finding
counted twice. The claim has one degree of freedom: quiet punishment happens at
a higher pre-move evaluation.

And the two-group split is really a gradient. P(punishment is quiet) by pre-move
eval: 37% at <=0, 36% at 0-150, 42% at 150-350, **63% above +350**. Flat, then a
jump. The 43% headline averages over that. Post-hoc; wants pre-specified
re-testing before it is quoted as a finding rather than a description.

### Two regimes, split by how good the position was

The paid half of the quiet-punishment question. If the punishment is a *delayed
tactic* — material, just arriving on move 3 or 5 instead of move 1 — the remedy
is calculation depth and it folds into the forcing-layer work. If it is
*positional decay* the remedy is a different skill entirely.

```bash
python3 chess/scripts/pvplayout.py /home/claude/features
```

Pre-specified: from the position immediately after the played move, depth 16,
walk the PV up to 10 plies, material balance from my POV read at the END of the
window so a capture-and-recapture nets to zero. Delayed tactic := PV mates
against me OR balance ends >=150cp worse. Controls run identically — without
them "material moved" means nothing, since it moves in ordinary play too.

| | n | delayed tactic | median material change |
|---|---|---|---|
| quiet-punished | 143 | **27.3%** | 0 cp |
| forcing-punished | 187 | 42.8% | -100 cp |
| controls | 330 | 15.8% | 0 cp |

Quiet vs controls **+11.5 pp, permutation p = 0.0054**. Real but small: about
three-quarters of quiet punishment never becomes material at all, and the median
case loses *exactly nothing* over the next ten plies. It just gets worse.

The gradient is the actual finding. Control baseline is flat across the same
bands (15 / 16 / 12 / 19%), so this is not level positions simply being sharper:

| eval before the move | n | delayed tactic | median material change |
|---|---|---|---|
| <=0 | 32 | **62%** | -225 cp |
| 0 to +150 | 37 | 27% | -90 cp |
| +150 to +350 | 30 | 17% | 0 |
| +350 and up | 44 | **9%** | 0 |

#### All 330 hot-zone judgment drops, by how they are punished

| eval before | forcing reply | delayed tactic | positional decay |
|---|---|---|---|
| <=0 | 63% | 23% | **14%** |
| 0 to +150 | 64% | 10% | 26% |
| +150 to +350 | 58% | 7% | 35% |
| +350 and up | 37% | 6% | **57%** |
| **overall** | **57%** | **12%** | **32%** |

#### What this changes

**The forcing layer is bigger than H2 alone said.** 57% forcing replies plus 12%
delayed tactics means **69% of the hot zone is tactical**. The pre-move check
takes the immediate 57% directly and the delayed 12% is the same skill run a
move deeper. This strengthens the case for the check as the first habit.

**There are two regimes, and the pre-move eval selects between them.** Level or
worse, the hot zone is 86% tactical and the check plus a little depth covers
nearly all of it. Above +350 it inverts: 57% positional decay, where no forcing
check and no amount of calculation depth helps.

**The +350 band belongs with the conversion problem, not the blunder problem.**
Forty positions where I was winning, played a considered quiet move, lost
>=200cp, and material never moved. That is the same failure as the 63.9%
conversion-from-won-positions figure and the 53.2% small-edge endgame number,
observed at move 17 instead of at endgame entry. It should stop being treated as
a residual of H2 and start counting as mechanism for the conversion target the
README already ranks second.

**Group P shrinks again by comparison.** In winning positions, hanging-material
errors were already capped at ~24% of blunders; this says most of what remains
up there is positional, not a missed tactic at any depth.

**Caveats.** The eval-band cut is post-hoc — built from the two-group difference
in the section above — so it wants a pre-specified re-test before it reorders the
drill queue. End cells are n=32 and n=44. A 10-ply window misses tactics that
take longer, which biases *toward* calling things positional; a 16-ply rerun
would test that. And this is depth-16 judgment about what should have happened
next, not a record of what did happen in the games.

## The opening book, recovered from move times

Added Aug 2026. `openings.py`. This is the first section of the README that
uses **no evals at all** for its main result, so the depth-12 caveat does not
touch it; the only engine work is the optional audit at the end, which is run
at depth 20 on a few dozen positions.

The method rests on one measured gap:

| | mean seconds |
|---|---|
| own moves inside the book | **1.38** |
| the first own move outside it | **2.53** |

n = 3,206 and 1,669 respectively. That separation is large enough that the
repertoire tree falls straight out of the clock data without any judgement
about which moves are good.

**Scope: 1,772 Lichess games, 2025-08-31 → 2026-08-19, 3+2 and 5+0**, from the
raw 2025 file plus the 2026 corpus. 882 White / 890 Black.

The raw file is a **convenience here, not a necessity**, and the command below
would produce the identical 1,772 games from `2025q3` + `2025q4` + the 2026
corpus — verified, 29 + 232 + 1,511. It is used because this analysis wants
clocks and not evals, so the cheaper file suffices; it is *not* used because
the annotated blocks are missing anything. Do not infer an eval gap in this
window from the file choice. There isn't one. **chess.com is excluded**: the export
gap means it contributes ~140 games to this window, which is too few to change
anything and enough to muddy the scope statement. Re-run with the two
chess.com blocks and `--user-map` if that ever matters.

Reproduce with:

```bash
python3 chess/scripts/openings.py \
  2025=chess/data/jamorgan_blitz_2025_raw.pgn.gz \
  2026=chess/data/jamorgan_blitz_2026_analyzed.pgn.gz \
  --since 2025-08-29 --min-reps 25 \
  --engine /home/claude/sf/x/usr/games/stockfish --engine-depth 20
```

`--tc` takes a comma-separated list (the `outcomes.py` convention, not
`longitudinal.py`'s). Default is `180+2,300+0`.

### Two things that will silently corrupt this if you rewrite it

**Nodes must be keyed by (colour, EPD), not EPD.** The position after `1.d4 e5`
arises both when he plays the Englund and when an opponent plays it against
him. Pooling the two gave `1.d4 e5 2.dxe5` a spurious 307 reps at 0.69 share —
the denominator was counting his Black games, where the move was not his to
make. Every share in the Englund lines was wrong until this was fixed. It is
the same class of error as the `CHESS_USER` silent-zero documented above:
plausible output, wrong population.

**Plies 1 and 2 carry no usable clock.** Lichess writes the initial clock for
both first moves regardless of what was actually spent, and only applies the
increment from ply 3 on. So `1.d4` and `1...c6` measure 0.00s by construction,
not by measurement. `openings.py` time-exempts those two plies and judges them
on share alone; an earlier version that did not divided by zero, which was
lucky — the quiet failure would have been to report every game as leaving book
at move 1.

### Validation gate

`openings.py` re-derives mean seconds per own move at moves 16–20 in the 2026
corpus before doing anything else, and hard-exits on mismatch:

| | measured | README |
|---|---|---|
| 180+2 | 8.37s | 8.4 |
| 300+0 | 7.78s | 7.8 |

Clock arithmetic is the single thing in this analysis that can be wrong
without looking wrong, so it is gated against a figure published from a
completely different script.

### First-move adherence is near-total, with a hole

| | | |
|---|---|---|
| 1.d4 as White | 881 / 882 | 99.9% |
| 1…c6 vs 1.e4 | 540 / 541 | 99.8% |
| 1…e5 vs 1.d4 | 254 / 256 | 99.2% |

Against anything else as Black there is **no settled reply at all**. 1.c4 (18
games) splits …e5/…Nc6/…d5 15/2/1; 1.e3 (12) splits …e5/…c6/…c5 6/5/1; 1.b3
(10) splits 7/2/1; 1.g3 (9) splits …d5/…e5 4/4. Adding 1.d3, 1.f4, 1.Nc3,
1.g4, 1.b4: **~70 games a year, book depth 0.** 1.Nf3 is the exception and is
prepared (…d5, 18 of 19).

### The book itself

Book node = ≥25 reps, top-move share ≥0.90, mean spend <3.0s. Descriptive, not
a pre-specified test; both thresholds are conventions, though 3.0s sits just
above twice the in-book mean rather than being picked freely.

**White — Accelerated London, depth 3, universal.** 2.Bf4 and 3.e3 against
literally every setup, and they are the fastest moves in the corpus:

| line | reps | mean s |
|---|---|---|
| 1.d4 d5 2.**Bf4** | 439 | 1.28 |
| 1.d4 Nf6 2.Bf4 d5 3.**e3** | 137 | 0.92 |
| 1.d4 d5 2.Bf4 Nc6 3.**e3** | 121 | 1.02 |
| 1.d4 e6 2.Bf4 d5 3.**e3** | 118 | 0.99 |
| 1.d4 Nf6 2.**Bf4** | 139 | 1.45 |
| 1.d4 e6 / g6 / c6 / d6 2.**Bf4** | 81 / 49 / 28 / 27 | ~1.4 |

**Black vs 1.e4 — Caro, depth 4–6.** 2…d5 is automatic against every second
move (2.d4 214×, 2.Nf3 189×, 2.Bc4 56×, 2.Nc3 36×, all ~1.3s).

| line | reps | mean s |
|---|---|---|
| 2.Nf3 d5 3.exd5 **cxd5** | 114 | 0.81 |
| 2.Bc4 d5 3.exd5 **cxd5** | 55 | 0.51 |
| 2.d4 d5 3.e5 c5 4.c3 **Nc6** | 53 | 1.09 |
| 2.d4 d5 3.exd5 **cxd5** | 52 | 1.40 |
| 2.d4 d5 3.e5 c5 4.c3 Nc6 5.Nf3 cxd4 6.cxd4 **Bg4** | 51 | 1.67 |

**Black vs 1.d4 — Englund, and the most interesting row in the section.** The
main line is played 100% of the time to move 8, but the clock climbs steadily:

| ply | move | reps | share | mean s |
|---|---|---|---|---|
| 3 | 2…Nc6 | 160 | 1.00 | 1.29 |
| 5 | 3…Qe7 | 128 | 0.98 | 1.55 |
| 7 | 4…Qb4+ | 51 | 1.00 | 1.39 |
| 9 | 5…Qxb2 | 42 | 1.00 | 1.81 |
| 11 | 6…Bb4 | 32 | 1.00 | **3.75** |
| 13 | 7…Qa3 | 27 | 1.00 | **3.41** |
| 15 | 8…Qa5 | 12 | 1.00 | **5.08** |

Share never drops. Spend nearly quadruples. **The moves are still known and
have stopped being trusted** — from move 6 on he is re-deriving a line he
plays unanimously. This is the one pattern in the section that the share
column alone would have missed entirely, and it is the argument for measuring
book by time rather than by move frequency.

### Book depth by family

| family | games | median depth |
|---|---|---|
| Black vs 1.e4 | 541 | 3 |
| White 1.d4 d5 | 439 | 3 |
| White 1.d4 Nf6 | 139 | 3 |
| Black vs 1.d4 | 256 | 2 |
| Black vs 1.Nf3 / 1.c4 / 1.e3 / 1.b3 | 19 / 18 / 12 / 10 | **0** |

Depth 2–3 sounds shallow and partly is an artifact of the ≥25-reps rule: the
tree fans out faster than reps accumulate, so a line can be genuinely known
and still fall below the bar. Read the per-line tables above, not this one,
for how deep any particular line runs. What the family table *is* good for is
the last row.

### Where the book stops

Nodes at ≥25 reps that fail the book test:

| line | reps | share | mean s | alternatives tried |
|---|---|---|---|---|
| 1.d4 d5 2.Bf4 Nc6 3.e3 Nf6 4.**?** | 78 | 0.63 | 3.76 | Nf3 49, c4 23, Bb5 4, Bd3, Be2 |
| 1.d4 c6 2.Bf4 d5 3.e3 Bf5 4.c4 e6 5.Nc3 Nf6 6.**?** | 25 | 0.56 | 3.14 | Qb3 14, Nf3 10, cxd5 |
| 1.d4 Nf6 2.Bf4 d6 3.e3 g6 4.h3 Bg7 5.**?** | 29 | 0.62 | 2.56 | Bh2 18, Nf3 8, c4 3 |
| 1.d4 g6 2.Bf4 Bg7 3.e3 Nf6 4.**?** | 50 | 0.82 | 1.71 | Nf3 41, c4 9 |
| 1.e4 c6 2.Nf3 d5 3.exd5 cxd5 4.d4 **?** | 88 | 0.86 | 1.21 | Nc6 76, Bg4 12 |
| …4.Nc3 Nc6 5.d4 Bg4 6.Be2 **?** | 28 | 0.68 | 2.53 | e6 19, Nf6 9 |
| 1.e4 c6 2.d4 d5 3.e5 c5 4.Nf3 Nc6 5.c3 **?** | 63 | 0.84 | 1.98 | cxd4 53, Bg4 10 |

The first row is the largest single hole in the repertoire: the standard
London tabiya, reached 78 times a year by two move orders, costing 3.76s and
resolved five different ways.

### The engine audit: is the fast move the right move?

Move times establish that a move is *prepared*. They say nothing about whether
it is *correct*, and that is the one question this method structurally cannot
answer. So `--engine` re-checks the top nodes at depth 20 with multipv 4 and
reports centipawns lost against the engine's first choice, from the mover's
point of view.

**44 of the 59 audited nodes are within 15cp of best.** The book is mostly
sound. The exceptions split into two kinds that must not be quoted as one
number:

**Repertoire choices, not errors.** `1.d4` (−16 vs 1.e4), `2.Bf4` (−19 vs
2.c4), `1…e5` the Englund itself (−101 vs 1…Nf6). These are the known price of
the openings, paid deliberately, and no amount of study removes them. Do not
report them as mistakes.

**Moves inside a chosen line that the engine dislikes:**

| line | reps | cost | engine prefers |
|---|---|---|---|
| Englund 5.Bd2 **Qxb2** | 42 | −62 | Qc5 |
| 1.d4 e5 2.d5 **f5** | 26 | −84 | Bc5 |
| 1.e4 c6 2.Bc4 d5 3.exd5 cxd5 4.Bb3 **a5** | 36 | −53 | Bf5 |
| 1.e4 c6 2.Nf3 d5 3.e5 **c5** | 47 | −34 | Bg4 |
| 1.d4 Nf6 2.Bf4 d6 3.**e3** | 33 | −28 | Nc3 |
| 1.e4 c6 2.Nf3 d5 3.exd5 cxd5 4.d4 Nc6 5.Bb5 **Bg4** | 33 | −24 | Qa5+ |

`Qxb2` is the one to take seriously: 42 reps a year, played in 1.81s at 100%
share, and the line it enters is exactly where the clock spend triples. That
is a single coherent story rather than six independent findings — the move he
is surest of walks into the position he has to solve from scratch every time.

**Caveats on the audit.** Depth 20 in the opening is not theory and the ranking
of near-equal moves at that depth is not stable; treat anything under ~30cp as
noise rather than a verdict, and check the named lines against an actual
reference before rewriting them. The `n × cost` column in the script output is
a sorting device, not a claim about rating points.

### What this does not establish

Nothing here is tested against **results**. Book depth is not shown to predict
score, the flagged moves are not shown to lose games, and no claim in this
section has been through a permutation test. It is a description of what is
prepared and what is not. The obvious follow-up — does leaving book early
predict anything downstream, controlling for opponent strength — is listed
under open threads and is not answered here.

The follow-up that would test it is written up as open thread 8, where the
clock half of it is closed on a power calculation before being run: own clock
at move 30 has sd ~42s, the predicted effect is 3–4s, and the corpus is short
by an order of magnitude. **The eval half has now been run — see the next
section. It is null.**

It also does not revisit the standing finding that **openings are a relative
strength and there is no reliable opening-phase deficit**. The gaps above are
gaps in *preparation*, measured in seconds; the eval-based work continues to
find no opening-phase problem, and the two are consistent. Time lost at move 4
is a clock cost, not an evaluation cost.

### Leaving book early does not produce a worse position

Thread 8 channel A, run Aug 2026. **Pre-specified in
`chess/scripts/thread8a_prespec.md`, which was written and committed before any
output was inspected** — read it rather than taking this section's word for the
rule.

```bash
python3 chess/scripts/thread8a.py /home/claude/features
```

Validation-gated on the `firstdrop.py` precedent, four gates, all hard-exit:
`openings.py`'s clock gate (8.37s / 7.78s at moves 16–20); the full-window
rebuild reproducing 1,772 games, in-book 1.38s, out-of-book 2.53s and `1.d4`
881/882; the features run being the 5,636-game eight-block one; and the
full-window eval@12 distribution (n = 1,641, sd 264 against a published ~1,643
and ~265). All four pass.

**Held-out by construction.** Book status is defined partly *by* move times, so
the node table is built on 2025-09-01 → 2026-04-30 (832 games) and only games
from 2026-05-01 → 2026-08-19 are scored (938 games, 871 with a usable eval@12).

Exposure is `report_depth`'s book depth, unchanged. Outcomes: **O1** `cp_after`
of own move 12 (primary — an own move's `cp_after` carries no POV trap),
**O2** share ≤ −100cp there, **O3** reached ≥ +200 in the middlegame. Test is
the within-family Spearman correlation, pooled sample-size-weighted, with
depth permuted **within family**, 10,000 draws, seed 23. Family is the control
that matters: book depth is close to determined by the opponent's choice, so an
uncontrolled correlation would mostly measure which openings are easy to face.
Five families cleared the pre-set ≥30-game bar (781 of 938 games).

| outcome | n | pooled rho | p |
|---|---|---|---|
| **O1 eval@12 (primary)** | 723 | **−0.056** | **0.14** |
| O2 share ≤ −100cp | 723 | +0.007 | 0.84 |
| O3 reached ≥ +200 | 781 | −0.081 | 0.023 |

**Null on the pre-specified rule** (p < 0.01 on O1). O3 does not clear 0.01
either, so there is not even a flag to log. Covariate check passed without
needing the robustness run: pooled rho(depth, opp_elo) = +0.054, below the
0.10 trigger.

#### Resolution, and a correction to the published figure

**This test detects an 80cp difference** at 80% power, alpha 0.01, two-sided.

The open-threads section published 45cp pooled and 64–90cp within family. That
table is computed on all **1,772 full-window games**; the held-out design
scores only 938 of them, and the median split lands 150 shallow against 573
deep. **The real held-out resolution is 80cp, not 45cp**, and the earlier
figure should not be quoted for this test. A null is worth nothing without its
resolution attached — so: no effect larger than ~80cp, and nothing about
effects smaller than that.

#### The direction is the informative part

All three point estimates lean **opposite** to the hypothesis — deeper book
associates with marginally *worse* eval@12 and *fewer* winning middlegames, not
better. Descriptively, shallow games average +48cp at move 12 against deep
games' +25cp. None of this is significant and none of it should be quoted as an
effect. What it does rule out is a real benefit sitting just under the
resolution floor: if leaving book early cost 40–70cp, the point estimates would
lean the other way and simply fail to clear p < 0.01. They do not.

This is consistent with everything else the project has found about the
opening. Preparation gaps cost **seconds**, not centipawns.

#### Three limitations, stated plainly

1. **The held-out node table is thin.** 832 training games against the
   published 1,772-game tree, so with `min_reps` 25 the book is sparser and
   depth compresses: max observed depth is 4, and 42% of test games sit at
   depth 3. That is measurement noise in the exposure and it biases **toward**
   null. Relaxing `min_reps` would fix it and would also be post-hoc tuning of
   the instrument after seeing the answer; it was not done.
2. **Two of the five included families have a degenerate median split**
   (`White 1.d4 Nf6` and `1.d4 e6` have zero shallow games), so they contribute
   to the rank-correlation test but nothing to the descriptive table.
3. **The 157 dropped games are the interesting ones.** Every family below the
   30-game bar is a rare opponent first move — exactly the `1.c4 / 1.e3 / 1.b3`
   territory where `openings.py` found book depth 0. The design cannot say
   anything about the unprepared openings, because there are not enough of
   them. That is the same ~70-games-a-year hole the openings section already
   records, seen from the other side.

#### One post-hoc observation, deliberately not promoted

`Black vs 1.d4` is the one family where the descriptive split separates: +46cp
shallow against −53cp deep, n = 49/68. That is the Englund, and going deeper in
it means reaching `5...Qxb2` — which the engine audit independently flagged at
−62cp against `Qc5`, at 42 reps a year and 100% share.

Two independent-looking things pointing the same way is exactly the shape of
the three findings already retracted here. It is one family out of five, it was
spotted by eye after the test came back null, the pooled test it sits inside is
null, and n = 68 in the deep arm. **Not a finding. Do not build on it.** If it
is ever worth pursuing, the pre-specified version is a single-family test of
the Englund main line against the `Qc5` alternative, on a block that does not
include these games.

## Open threads

Written to be picked up cold. Read this section plus `features.py`'s docstring
and you have the state; nothing below depends on remembering a conversation.

Setup for any of it:

```bash
pip install chess --break-system-packages
python3 /mnt/skills/user/github-access/scripts/github.py clone justinmorg/justinmorg.github.io
cd /home/claude && for f in justinmorg.github.io/chess/data/*_analyzed.pgn.gz; do
  gunzip -c "$f" > "$(basename "${f%.gz}")"; done
python3 justinmorg.github.io/chess/scripts/features.py \
  2024H2=jamorgan_blitz_2024h2_analyzed.pgn Q1-2025=jamorgan_blitz_2025q1_analyzed.pgn \
  Q2-2025=jamorgan_blitz_2025q2_analyzed.pgn Q3-2025=jamorgan_blitz_2025q3_analyzed.pgn \
  2026=jamorgan_blitz_2026_analyzed.pgn CC-2024Q4=chesscom_justinmorg_2024q4_analyzed.pgn \
  CC-2026=chesscom_justinmorg_2026febapr_analyzed.pgn \
  --tc 180+2,300+0 --user-map CC-2024Q4=justinmorg CC-2026=justinmorg \
  --out /home/claude/features
```

~100–140 s, and it should print **5,404 games / 178,684 own-move rows**. If it
doesn't, stop and find out why before running anything else.

**There are now two valid scopes, and you must know which one you are in.**
The seven-block invocation above is the tripwire the analysis sections below
were built against — keep using it to validate a fresh environment. Adding
`Q4-2025=jamorgan_blitz_2025q4_analyzed.pgn` gives **5,636 games / 186,191
own-move rows**, and the seven old blocks reproduce inside it unchanged
(verified: reached 2,865 / 63.9%; endgame entry 1,073 / 401 / 774 / 1,443; flag
wins 434 of 2,619; all seven per-block hang rates identical). Q4 is folded into
`longitudinal.py` and `outcomes.py` above; it is **not** folded into
`phases.py`, `material.py`, think-time, `oppmove.py`, `firstdrop.py` or
`forcingtest.py`, which remain seven-block results.

### 1. Opponent's previous move — controlled version — **DONE**

Resolved; see "What the opponent's previous move predicts" above. Numbering is
kept as-is because threads 2 and 3 are cross-referenced by number elsewhere in
this README.

Short version: the capture row split into recaptures (genuinely safe, −2.02 pp
against quiet) and fresh captures (+0.80 pp against quiet); the check row is
not identifiable under these controls; the created-threat row is definitional
and reverses once re-posed within material-hanging positions, with standing
threats **+6.28 pp** worse than newly created ones. Thread 2 is now the
highest-priority open item.

The raw table it started from, kept for the record:

| opponent's previous move | freq | my blunder rate |
|---|---|---|
| check | 8.8% | 7.95% |
| capture | 25.3% | 8.46% |
| pawn_break | 2.3% | 10.44% |
| quiet | 63.6% | 10.16% |
| created a threat | 18.0% | 11.58% |
| did not | 82.0% | 9.09% |

Forcing moves look *safe* and quiet moves look dangerous, which is the reverse
of the intuition. Two confounds have to die first: forcing moves shrink
`n_legal`, and the created-threat row is partly built in, since a standing
threat ≥150 guarantees the material exists to lose.

The prescribed stratum set included `in_check`, which turned out to be
unusable — it is perfectly collinear with the check arm of the exposure. That
is why the check row came back unanswerable rather than answered.

### 2. First major deterioration — **DONE**

Resolved; see "The first major deterioration: level games are decided early"
above. Short version: there is a moment — median fullmove 16, 59% of permanent
first drops in moves 13–25 at npm ≥ 13, and the permanent share is 55–57% in
all seven blocks. But conditional on move number, hazard is highest at *full*
material and declines as pieces come off, so the npm 19–13 prediction was a
composition effect — the `material.py` crossing deficit was the hot zone seen
through a material lens. Mechanism: 70% of permanent hot-zone drops involve no
hanging material, 71% follow a quiet opponent move, and they get *more* time
than baseline (median 8s vs 6s, only 13% snap moves) — judgment failures on
considered moves. The manual-review question (thread 3) is now the
highest-priority open item, re-pointed at these positions.

The original spec, kept for the record:

A groupby on `moves.csv.gz`, no new data. Per game, first ply where
`drop_cp >= 100 / 200 / 300`; temporary vs permanent from whether `cp_before`
recovers within N later own moves. Deliberately not a stored column — the
thresholds and recovery window are the thing being chosen.

Most useful against the `even` bucket in `games.csv`, which currently has no
error-timing profile at all despite being 529 games scoring 40.5%.

**`material.py` sharpened this considerably.** The level-position deficit
against comparable games is concentrated at npm 19–13 (−2.5 to −4.3) and is
gone by npm 11. So the prediction is specific: in games level in the early
middlegame, the first major deterioration should cluster in that material band.
If it does, "loses the thread in the early middlegame" is the mechanism and the
drill target follows. If the first drop is spread evenly across material, the
deficit is not about a moment and the framing needs rethinking. Either answer is
worth having, and it is still a groupby on data already in hand.

### 3. Manual review — re-pointed at the hot zone

The only item that ends in a training change rather than another table, and
**now the highest-priority open item**. Thread 2 relocated the target: the
review set is no longer level endgames but the 633 permanent hot-zone first
drops — quiet, piece-heavy, level positions at moves 13–25 where the game was
decided on a considered move. `firstdrop.py`'s output identifies them by
`(gid, ply)`. The question a human review answers is the one no groupby can:
bad plans, wrong pawn breaks, drifting pieces, or tactics two moves deep?

The top 40 are now on the drill page as **group R** with a per-position
reflection box and JSON export — see "Group R: the reflection set" above. The
working form of this thread is: write notes there, export, read the batch
together for the pattern.

**All 40 notes done (Aug 2026) — this thread's data collection is complete.**
See "All 40 group R notes: what the batch says" above for the full reading.

The first nine generated a hypothesis that `forcingtest.py` then split into a
null and a large effect — see "The forcing layer" above. Worth noting how that
went: the notes' most *vivid* content ("I never saw the hanging queen") was the
half that tested null, and the half stated more flatly ("I didn't detect any
threats here") was the half that held. The full batch made that lesson sharper
rather than weaker — ~30% of the 40 notes centre on a missed own resource,
which is the H1 claim that tests null at p = 0.93. Introspective salience is
not evidence of frequency; the notes are valuable as a hypothesis source, and
every hypothesis they raise gets tested against a matched control before it
counts.

**What remains of this thread is testing, not collecting.** Two hypotheses came
out of the batch: pawn moves versus piece moves (a groupby on existing columns,
needs pre-specification and a held-out check) and planlessness as the mechanism
behind positional decay (not currently measurable — thread 6's design problem).
The quiet-punishment residual now has a *description* from the notes but no
test. Writing more R cards is not the bottleneck; the top-40 selection is
already the tail of the distribution and more of the same would not change
what the batch supports.

The original endgame framing, kept for the record. **Its priority had already
dropped since `material.py`.** The 42.7% over 774 games is real,
but the material curve shows that is roughly *par* for games still alive at that
material level — the level-position deficit against comparable games has closed
to ~0 by npm 11. The 42.7% looks alarming next to 50%, and next to the right
benchmark it is unremarkable. Level endgame technique is no longer the strongest
evidence-backed item; thread 2 is.

Still worth doing eventually, and the one-to-three-pawn edge at 53.2% over 401
games remains a separate and better-motivated target, since converting a small
edge is not the same skill as holding equality.

Pull 30–50 from `games.csv` where `eg_entry_cp` is in [−100, +100], play through
them, and look for the human pattern. Not automatable, which is why it keeps
slipping.

### 4. Cheap groupbys, no new instrument

Columns exist and are unused: `queens_on` (with the controls the queen question
needs — phase, eval, complexity, material, clock), the complexity block as
covariates rather than findings, and game-trajectory typologies. Low expected
value individually; each is minutes of work.

### 5. Middle of the spend curve

`multipv.py` covers only ≤2s and ≥8s. The 2–8s band, ~1,000 positions and
~25 min at depth 16, would fill in the curve. **Motivation is weak now** — it
was going to test a bimodality prediction that died with the interaction. Do it
only if some other question needs the middle.

### 6. A real difficulty instrument

The open question the corpus cannot currently answer: think time may be a
*marker* of not having seen the threat rather than a cause of failing to handle
it. `n_within_100` measures solution narrowness, which is not the same thing —
a forced recapture is maximally narrow and trivially easy.

Capturing human difficulty needs a different annotation, not more depth:
whether the saving move is a capture or a quiet retreat, whether the threat is
one or two moves deep, whether the correct reply is forward or backward. That's
a design problem first. Don't start it by running an engine.

### 7. Does severity skew fast? — open, cheap, and to be handled carefully

Thirteen group R notes in, several of the *costliest* drops were 1–3 second
moves ("this one was just me moving too fast"), against a hot-zone median of 8s
and only 13% at ≤2s. Possible that severity and spend run opposite to
frequency: most hot-zone errors are considered moves, but the worst ones are
snap moves. Testable with one groupby — `wp_error` against `spend` within the
hot-zone set, game-level resampling for CIs.

**Handle with the same caution as the rest of the think-time material.** The
spend/error gradient is confounded by difficulty in both directions, and
nothing here would license "move slower" any more than the earlier result
licensed "move faster." At most this identifies a subset, not a remedy. n is
also small: 13 notes, a handful of fast ones.

### 8. Does leaving book early predict anything? — **DONE, null**

**Resolved Aug 2026. Channel A was run and is null; channel B was already dead
on a power calculation.** See "Leaving book early does not produce a worse
position" above for the result, and `thread8a_prespec.md` for the rule as it
was written beforehand.

Short version: within-family Spearman on 781 held-out games gives O1 (eval@12)
rho = −0.056 at **p = 0.14**, O2 p = 0.84, O3 p = 0.023 — nothing clears the
pre-specified 0.01, so there is not even a flag. **Resolution is 80cp, not the
45cp this section originally published** (that figure was for all 1,772
full-window games; the held-out design scores 938). All three point estimates
lean opposite to the hypothesis, which rules out a real benefit hiding just
under the floor. Thread 8 is closed; the corrected scoping below is kept for
the record.

The original spec, kept for the record:

`openings.py` produces a per-game book depth: consecutive own moves from move 1
that are book moves. Nothing has been done with it. The question splits into two
channels, and **they are not equally viable** — the clock channel was the
obvious one and is the one that cannot be run.

**Channel B, clock — not testable at this corpus size. Do not attempt it.**
The appealing version was "does a 3.8s hole at move 4 still exist at move 30."
It does not survive a power calculation. Own clock at move 30 in the largest
held-out cell (Black vs 1.e4 at 300+0, May–Aug 2026) has **sd 41.5s across 129
games**, and only about half of games reach move 30 at all. Splitting that cell
by book depth gives ~65 per group, which detects a difference of **~25s** at 80%
power and alpha 0.01. Pooling all families within 300+0 gets ~225 per group and
detects **~15s**.

The predicted effect is **3–4 seconds**: the measured book gap is 1.15s per
move (2.53 out of book against 1.38 in it), over the two or three extra
out-of-book moves that separate a shallow game from a deep one. So the test is
underpowered by a factor of four to eight against its own hypothesis, and
detecting 3.5s at sd 46 would need roughly **4,000 games per group** — an order
of magnitude beyond the corpus, and beyond what any realistic number of new
batches would supply.

More to the point, **the quantity of interest is already measured directly**.
Seconds spent on out-of-book moves is observed at the source, per move, with no
inference required. Asking whether it is still visible twenty moves later is
asking whether a small measured quantity survives being swamped by the variance
of everything that happens in between. It will not, and it does not need to:
the cost is the 3.76s at the London move-4 tabiya, not some echo of it at move
30. Record the direct figure; do not chase the downstream one.

**Channel A, evaluation — viable, cheap, and expected null.** Does leaving book
early produce a worse position? Outcomes: eval after own move 12, share of
games at ≤−100cp there, whether a ≥+200 middlegame is reached. All three are
already columns in `features.py`'s `games.csv`.

Resolution, from all **1,772** games in the window, every one of which is
annotated — 29 from the Q3 2025 slice (which runs to 2025-09-30), 232 from Q4
2025, 1,511 from the 2026 corpus. 1,643 of them carry a usable eval at own
move 12, which has **sd 265cp**:

*Corrected Aug 2026.* The first version of this thread claimed channel A was
limited to "the Q4 2025 slice plus the 2026 corpus" and called the raw 2025
file "a real limitation" for it. Both were wrong: the Q3 slice covers the
window's opening month, and the README already states that the raw file is
fully covered by slices. The error came from reaching for the raw file because
the *clock* analysis had used it, and not re-checking whether the eval analysis
needed to. Nothing downstream moves — n goes 1,616 → 1,643, sd 264 → 265, and
the resolution table below is unchanged to the digit.

| games per group | detectable at |
|---|---|
| 200 | 90cp |
| 400 | 64cp |
| 800 | 45cp |

Pooled, this resolves 45cp. Within family — which is the version that actually
answers the question, see below — the larger families give 200–400 per group
and resolve 64–90cp. That is a real but coarse instrument: it would catch
"unprepared openings produce materially worse positions" and would miss
anything subtler.

**Controls.** Opponent Elo and colour. The one that matters is **opening
family**: book depth is close to determined by the opponent's choice, so a raw
correlation would mostly measure which openings are easy to face rather than
anything about preparation. The comparison has to be shallow-vs-deep *inside*
`1.d4 d5`, inside the Advance Caro, and so on. That control is what costs the
power in the table above, and it is not optional.

`TimeControl` need not be split for channel A — eval at move 12 is inside the
window the README verifies as poolable, and the format split only binds on
clock-dependent quantities past move 25.

**Held-out design, and why.** Book status is defined partly *by* time: a node
needs mean spend under 3.0s to qualify. Regressing a time-derived predictor on
a time-derived outcome is circular, and the bias runs in exactly the direction
the hypothesis predicts. With ≥25 reps per node any one game's contribution to
its own node's classification is small, but small is not zero. So **build the
node table on Sep 2025–Apr 2026 and score games from May–Aug 2026 only.** This
matters much less for channel A than it would have for channel B — eval is not
time-derived, so the circularity is second-order there — but the corpus has
three retracted findings and a held-out split is cheap.

**Pre-specified decision rule.** Channel A, stratified permutation test by
family, game-level resampling, p<0.01 given three outcome columns. **Honest
prior: null.** Every opening-phase test in this README has come back null, eval
at move 12 is fine, and the gaps `openings.py` found cost seconds rather than
centipawns. State the detectable-at figure with the result whichever way it
lands, the way the chess.com diversity test did — a null is worth nothing
without its resolution attached.

### Do not re-chase

- **Pawn moves being more dangerous than piece moves.** Pre-specified, null:
  standardized +0.40 pp on a ~9.5% base at p = 0.12 over 106,237 rows, and the
  exploratory hot-zone cut is +0.11 pp. Note the raw comparison runs the *other*
  way (pawn 9.44% vs piece 9.61%), so an uncontrolled version of this would
  read as "pawn moves are safer" and be equally wrong. Fifth notes-derived
  hypothesis to test null or reverse.
- **Book depth predicting position quality.** Pre-specified, held-out, null:
  eval@12 rho = −0.056 at p = 0.14, and all three outcomes lean *opposite* to
  the hypothesis. Resolution 80cp, so effects smaller than that are untested —
  but a real benefit would have leaned the right way. The Englund sub-result
  (`Black vs 1.d4`, +46 shallow vs −53 deep) is post-hoc, one family of five,
  inside a null pooled test, and is not a finding.
- **H1, missed own forcing moves.** Blunder positions contain no more available
  captures/checks than matched controls (28% vs 28%, p = 0.93), and in controls
  where the best move was forcing he played it 87% of the time. The mirror
  claim (H2) is the real one. If a future reflection note says "I never saw
  that capture" — and they will, it's the most memorable kind of miss — that
  intuition has already been tested against controls and lost.
- **Severity skewing fast inside the hot zone.** Pre-specified test failed:
  T1 non-monotone, T2 null at p = 0.31. A post-hoc lean survives (+0.041
  standardized, p = 0.008) and is logged in the thread 7 section as a flag, not
  a finding. Do not re-run without a held-out block.
- **Fast opponents being better prepared** (the preparation explanation for the
  C2 clock result). Eval at move 12 is flat across opponent pace terciles.
- **The standing-threat and first-drop findings being one event.** Tested
  directly: 2.2% move-level overlap, odds ratio 1.30 [0.95, 1.75] at p = 0.12
  exposure-matched, and B still costs 4.9 pp in games that already have an A.
  They are separate failure modes whose loss budgets add. See "Three failure
  modes, not one".
- The gap-by-difficulty interaction. Held out at p = 0.47. Third instance of
  monotone-ordering-plus-mechanism-plus-no-replication.
- The June 2025 hanging-material dip, and the Q1→Q3 drop.
- **The Jan/Feb 2026 rating peak.** 1508 on 2026-02-06 is the all-time high and
  came off a visible win run, but the selection-aware test is null on every
  quality metric (primary p = 0.55), the streak itself is p = 0.08–0.17, and
  W1 beat its Elo expectation by exactly 1.0 SE. Resolution ~3cp per move on
  accuracy; the hanging-material arm was underpowered at 661 eligible moves, so
  *that* arm alone could be worth re-running if a future excursion is longer.
  Do not re-open it on the same window.
- The moves 13–25 apparent improvement.
- The chess.com `hung it myself` difference — open, but not cheaply resolvable;
  see that section for what it would actually take.

### Declined on purpose

LLM classification of error types (step 10 of the source outline) was
considered and rejected: it adds a measurement instrument with unknown error
rate to a project whose main asset is that its numbers survive re-testing. If
it's ever wanted, it needs a hand-labelled validation subset built first.

## What this is for

The corpus exists to study **converting winning positions into wins**, which is
the main identified weakness. Current focus (updated Aug 2026, after threads 1
and 2) is early-middlegame judgment in level, piece-heavy positions — the
largest loss flow — alongside the standing-threat re-scan and small-edge
endgame conversion. The earlier focus statement, kept for the record: endgame
technique, particularly
king and pawn endings. That's why the `[%eval]`/`[%clk]` pairing matters: the
questions being asked are about *where* an advantage evaporated and *how much
clock was left when it did*, which needs both series aligned ply by ply.
