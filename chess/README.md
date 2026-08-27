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
│   ├── jamorgan_blitz_2025q2_analyzed.pgn.gz Q2 2025 slice, depth-12 annotated
│   ├── jamorgan_blitz_2025q3_analyzed.pgn.gz Q3 2025 slice, depth-12 annotated
│   ├── chesscom_justinmorg_blitz_raw.pgn.gz  all chess.com blitz, unannotated
│   ├── chesscom_justinmorg_2024q4_analyzed.pgn.gz
│   │                                      chess.com Sep-Dec 2024, depth-12
│   └── chesscom_justinmorg_2026febapr_analyzed.pgn.gz
│                                          chess.com Feb-Apr 2026, depth-12
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

That argument got stronger in Aug 2026 in two ways. Q2 2025 was annotated
(1,559 games) and a game-level label-shuffle across all five blocks — 12,259
eligible moves — returns p = 0.71: no block differs from any other. The apparent
Q1→Q3 2025 drop was noise; see "Q2 2025, and why the Q1→Q3 drop was not real".
Second, the same hanging-material rate was measured on 808 concurrent chess.com
games (5.51% vs 5.48% on the date-matched
Lichess games) against opponents 516 Elo lower on the nominal scale. See "The
chess.com corpus" below — the plateau is not an artifact of one site's pool.

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
  2024H2=h2.pgn Q1-2025=q1.pgn Q2-2025=q2.pgn Q3-2025=q3.pgn 2026=corpus.pgn \
  CC-2024Q4=cc_2024q4_analyzed.pgn CC-2026=cc_2026febapr_analyzed.pgn \
  --tc 180+2,300+0 --user-map CC-2024Q4=justinmorg CC-2026=justinmorg

# clock state for the same buckets — takes bare paths, not LABEL=path
python3 chess/scripts/clockstate.py h2.pgn q1.pgn q2.pgn q3.pgn corpus.pgn \
  --tc 180+2,300+0
```

Note `--tc` takes a **comma-separated list**, unlike `longitudinal.py`'s single
value, and `--user-map` sets the player per block so Lichess and chess.com can
go in one call. Scope below is 3+2 and 5+0 across all seven annotated blocks —
**5,404 games**, every analyzed game bar seven (4 Lichess at 5+3/3+0, 3
chess.com at 300).

| block | games | reached ≥+200 | score \| reached | score \| never reached |
|---|---|---|---|---|
| 2024 H2 | 651 | 54.2% | 62.5% | 37.1% |
| Q1 2025 | 375 | 54.7% | 64.1% | 34.1% |
| Q2 2025 | 1,559 | 50.3% | 63.2% | 36.4% |
| Q3 2025 | 363 | 52.1% | 63.2% | 36.5% |
| 2026 | 1,511 | 53.9% | 65.6% | 32.0% |
| cc 2024 Q4 | 808 | 55.6% | 63.7% | 34.7% |
| cc 2026 Feb–Apr | 137 | 51.1% | 62.9% | 38.8% |

Pooled: **63.9% [62.2, 65.6]** from 2,865 games that reached a winning position,
**35.0%** from the 2,539 that never did. Flat across blocks, and the two
chess.com blocks land inside the Lichess spread on both columns — consistent
with the pool-calibration result elsewhere in this README.

Earlier revisions of this section gave that second figure as both 35.2% and
34.9%. The measured value is **34.95%** (887.5 points over 2,539 games),
recomputed from `features.py`'s `games.csv`; every per-block row in the table
above reproduces exactly. Use 35.0%.

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
| 2026 | 2,640 | 4.73% | 1.06% |

Game-level label-shuffle across all five blocks, 20,000 shuffles:

- hanging material: observed spread 0.92 pp, **p = 0.71**
- hung it myself: observed spread 0.29 pp, **p = 0.91**

No block differs from any other on either measure. The Q1→Q3 drop was sampling
noise in two small blocks, and Q2's tight interval now anchors the middle of the
series. Do not re-chase it — same category as the moves-13–25 block-selection
artifact recorded above.

This also **retracts a flag raised when Q2 was first measured**: Q2's `hung it
myself` rate of 1.30% looked elevated against the 1.00/1.06/1.08/1.06 of the
other blocks, and within Q2 it declined monthly (1.79 → 1.39 → 0.89). At p =
0.91 across blocks, none of that is real. Two large blocks landing high is what
noise looks like when most blocks are small.

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
does the tests; every p-value in this README comes from it, with the seed noted:

```bash
# do any of the five Lichess blocks differ?  spread 0.92 pp, p = 0.71
python3 chess/scripts/blockstats.py shuffle \
    2024H2=h2.pgn Q1=q1.pgn Q2=q2.pgn Q3=q3.pgn 2026=corpus.pgn \
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

**Why the pooled test overstated it.** Pooling the whole Lichess corpus put the
baseline at 1.15%, but the two date-matched sub-windows sit at 1.22% and 1.39%.
The homogeneity result says that spread is noise — which is exactly the point:
it is noise the pooled comparison silently absorbed into the *contrast*.
Homogeneity licenses pooling for comparisons *between* Lichess blocks. It does
not license using a pooled Lichess baseline against a block drawn from specific
weeks. Match the dates.

**Status: unresolved, and not cheaply resolvable.** Detecting a ~0.5 pp
difference on a ~1.2% base needs several times the current 3,175 chess.com
eligible moves. The remaining un-annotated chess.com 3+2 games number only 422
(351 from 2023, pre-repertoire; 71 from 2024). The only large block left is
1,071 games at 3+0, which is not verified as poolable. Either accept this as
open or generate new chess.com 3+2 games.

One observation worth keeping, on small numbers: in the 2026 chess.com block the
composition inverts — 15 of 26 floored hits are `hung it myself` against 11
`missed their threat`. Every other block measured, on either site, is roughly
3:1 the other way. On 26 hits that is not worth acting on, but it is the thing
to look at first if more chess.com data ever arrives.

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

~100 s, and it should print 5,404 games / 178,684 own-move rows. If it doesn't,
stop and find out why before running anything else.

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

### 2. First major deterioration

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

### 3. Manual review of level endgames

The only item that ends in a training change rather than another table. **Its
priority has dropped since `material.py`.** The 42.7% over 774 games is real,
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

### Do not re-chase

- The gap-by-difficulty interaction. Held out at p = 0.47. Third instance of
  monotone-ordering-plus-mechanism-plus-no-replication.
- The June 2025 hanging-material dip, and the Q1→Q3 drop.
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
the main identified weakness. Current focus is endgame technique, particularly
king and pawn endings. That's why the `[%eval]`/`[%clk]` pairing matters: the
questions being asked are about *where* an advantage evaporated and *how much
clock was left when it did*, which needs both series aligned ply by ply.
