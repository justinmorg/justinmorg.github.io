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
│   └── jamorgan_blitz_2026_analyzed.pgn.gz   canonical corpus (gzipped)
└── scripts/
    ├── annotate.py                           add depth-12 [%eval] to a PGN
    ├── merge.py                              fold new games into the corpus
    ├── hanging.py                            find winning positions where material hung
    ├── build_drills.py                       inject those into /chess-drills
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

## Hanging-material extraction

`hanging.py` finds the largest single source of thrown-away wins: middlegame
moves played while already winning, with material hanging.

```bash
python3 chess/scripts/hanging.py corpus.pgn light   # -> /home/claude/hits_light.json
python3 chess/scripts/build_drills.py               # -> chess-drills/index.html
```

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
localStorage total). Regenerate with `build_drills.py` rather than hand-editing;
priority drills key off `P1`…`Pn` so the original 1–21 ticks survive a rebuild.

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
