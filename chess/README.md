# chess

Canonical game corpus and analysis tooling for Lichess account `jamorgan`.

This folder is **not a published site** — unlike the other top-level folders in
this repo, there's no `index.html` here. It lives in the repo so the corpus and
scripts are findable and updatable from any session. (Pages does still serve the
files at `https://justinmorg.github.io/chess/...` since it publishes the whole
repo root; nothing here is secret, but nothing here is meant to be browsed
either.)

## Layout

```
chess/
├── data/
│   ├── jamorgan_blitz_2026_analyzed.pgn.gz   canonical corpus (gzipped)
│   ├── jamorgan_blitz_2025_raw.pgn.gz        2025 games, clocks only, NO evals
│   ├── jamorgan_blitz_2023_2024_raw.pgn.gz   2023-24 games, clocks only, NO evals
│   ├── jamorgan_blitz_2024h2_analyzed.pgn.gz Aug-Dec 2024 slice, depth-12
│   ├── jamorgan_blitz_2025q1_analyzed.pgn.gz Q1 2025 slice, depth-12 annotated
│   ├── jamorgan_blitz_2025q3_analyzed.pgn.gz Q3 2025 slice, depth-12 annotated
│   ├── chesscom_justinmorg_blitz_raw.pgn.gz  all chess.com blitz, unannotated
│   └── chesscom_justinmorg_2024q4_analyzed.pgn.gz
│                                          chess.com Sep-Dec 2024, depth-12
└── scripts/
    ├── annotate.py                           add depth-12 [%eval] to a PGN
    ├── chesscom_filter.py                    raw chess.com export -> blitz PGN
    ├── annot_inc.py                          resumable annotate — use for big jobs
    ├── longitudinal.py                       compare annotated blocks over time
    ├── merge.py                              fold new games into the corpus
    ├── hanging.py                            find winning positions where material hung
    ├── build_drills2.py                      rebuild the /chess-drills P set
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

### The three annotated slices

`jamorgan_blitz_2025q1_analyzed.pgn.gz` (375 games, 25,610 plies, 2025-01-02 →
2025-03-31) and `jamorgan_blitz_2025q3_analyzed.pgn.gz` (363 games, 25,019
plies, 2025-07-01 → 2025-09-30) are depth-12 annotations of two slices of the
raw 2025 file, committed so the longitudinal comparison below is reproducible
without redoing ~40 minutes of engine work. Full eval and clock coverage, no
duplicate GameIds. Q1 is the pre-climb baseline (mean rating 1317, mean
opponent 1317); Q3 is the plateau onset (1399 / 1396).

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
scripts, so all four blocks are directly comparable.

### What two years actually changed

Reproduce any of this with:

```bash
python3 chess/scripts/longitudinal.py \
  2024H2=h2.pgn Q1-2025=q1.pgn Q3-2025=q3.pgn 2026=corpus.pgn --tc 180+2
```

Drop `--tc` to check whether a finding is a time-control artifact — the script
then also prints band 26+ split by `TimeControl`.

Four-block comparison — 2024 H2 / Q1 2025 / Q3 2025 / 2026 — all restricted to
**3+2 only**, because the one real effect lands in the move band where formats
diverge. Blunder = own move drops the eval ≥200cp. Rates per own move:

| move band | 2024 H2 | Q1 2025 | Q3 2025 | 2026 |
|---|---|---|---|---|
| 1–12 | 3.58% [3.16, 4.00] | 3.70% [3.15, 4.24] | 3.53% [3.00, 4.12] | 3.27% [2.92, 3.64] |
| 13–25 | 10.74% [10.00, 11.49] | 11.43% [10.47, 12.41] | 11.00% [10.02, 12.02] | 9.85% [9.18, 10.52] |
| 26+ | 13.15% [12.34, 13.96] | 12.76% [11.80, 13.76] | 11.52% [10.56, 12.47] | 9.68% [9.04, 10.32] |

**Move 26+ is the only established improvement** — monotonic across all four
blocks, ~26% relative, non-overlapping intervals end to end, against opponents
who got stronger (mean opponent Elo 1257 → 1317 → 1396 → 1379).

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

| | 2024 H2 | Q1 2025 | Q3 2025 | 2026 |
|---|---|---|---|---|
| Hanging material (0.02 floor) | 5.02% [4.11, 5.93] | 5.23% [4.00, 6.54] | 4.31% [3.23, 5.46] | 4.73% [3.94, 5.57] |
| — missed their threat | 4.02% | 4.17% | 3.23% | 3.67% |
| — hung it myself | 1.00% | 1.06% | 1.08% | 1.06% |
| Reached ≥+200 in middlegame | 54.2% | 54.4% | 52.1% | 53.3% |
| Score from won positions | 62.5% [57.5, 67.4] | 64.3% [57.6, 70.7] | 63.2% [56.4, 69.8] | 63.2% [58.5, 67.9] |
| Eval after own move 12 | +81cp | +6cp | +9cp | −36cp |

All statistically indistinguishable across two years. `hung it myself` is
especially striking — 1.00 / 1.06 / 1.08 / 1.06 across 24 months.

The eval@mv12 row has intervals wide enough to be uninformative
(2024 H2 is [−18, +187]); the apparent decline tracks opponent strength rising
by ~120 Elo, not opening skill falling.

The rating climb through mid-2025 tracks the late-game accuracy gain; the
plateau since then tracks a middlegame hanging-material rate that has never
responded to anything. That is the argument for group P being deliberate
practice rather than more games — two years of play did not move it.

That argument got stronger in Aug 2026: the same hanging-material rate was
measured on 808 concurrent chess.com games (5.51% vs 5.48% on the date-matched
Lichess games) against opponents 516 Elo lower on the nominal scale. See "The
chess.com corpus" below — the plateau is not an artifact of one site's pool.

Caveat on all of the above: score rate sits at ~50% in every block by
construction, since Lichess matchmaking is self-correcting. Rating *level* is
the improvement metric; score rate is not, and neither is anything measured
against opponents whose strength tracks yours.

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
rating ~1234 → 1301). Only the second was annotated — see below. The 2023 block
sits at 800–1000 Elo where falling error rates are just a beginner improving,
which says little about the plateau.

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
| 2023 Jun–Nov | 362 | 21,312 | 351 at 3+2 | pre-repertoire — Englund absent entirely, Caro 16% in Jun–Jul |
| 2024 Jan–Apr | 1,667 | 100,969 | 1,071 at 3+0, 525 at 5+0 | Lichess is near-silent here |
| 2024 Sep–Dec | 811 | 52,097 | 808 at 3+2 | **annotated** — see below |
| 2026 Feb–Apr | 137 | 10,030 | all 3+2 | concurrent with the 2026 corpus |

Nothing between 2025-01 and 2026-01 was exported. A July 2025 file exists (~6
games at Elo 754–827) but failed to transfer three times; it is not in this set.

The Jan–Apr 2024 block is the largest single body of unanalysed play anywhere in
this project, and it fills a genuine Lichess hole — but it is 1,071 games of
**3+0**, the one clock regime this project has never verified as poolable. It
needs its own comparison, not a row in the existing table.

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

**One thing that may not replicate.** `hung it myself` comes in at 1.66%
[1.21, 2.19] on chess.com, against 1.00 / 1.06 / 1.08 / 1.06 across the four
Lichess blocks — the stability the section above singles out. The chess.com
interval's lower bound clears three of those four point estimates. But the
date-matched Lichess figure is 1.22% [0.49, 2.07], which overlaps it, so this is
a flag to watch as more chess.com blocks are annotated, not a finding.

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

## Update procedure

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

## What this is for

The corpus exists to study **converting winning positions into wins**, which is
the main identified weakness. Current focus is endgame technique, particularly
king and pawn endings. That's why the `[%eval]`/`[%clk]` pairing matters: the
questions being asked are about *where* an advantage evaporated and *how much
clock was left when it did*, which needs both series aligned ply by ply.
