# What a "hanging material" flag actually is (2026-11-25)

Exploratory, not pre-registered. Justin's question from 2026-11-21, parked until
the F block closed: the flagged hang errors are not one thing (sometimes a flat
hang, sometimes a missed best move after an opponent blunder, sometimes a
miscounted exchange); separate them by comparing the eval change with the
material change, and count how many flagged errors led to a sustained material
deficit. This is also the "rate is unmeasured" item from "Label audit" (the
depth-18 capture-and-evaluate check, applied to the corpus metric rather than
the cards).

**Not a re-test of F.** The per-block confirmed rates below are descriptive
only; the pre-registered result stands as run.

Scripts: `chess/scripts/hanganatomy/` (`extract.py` → `engine.py` →
`analyze.py`). Engine output: `chess/data/hanganatomy_d18.jsonl.gz`. Per-hit
table: `chess/data/hanganatomy.csv.gz`.

## Scope and tripwire

Every floored hit under the pre-registered outcome definition: `probe()` from
`hanging.py`, fullmove > 12, light npm > 14, cp_before >= +150, wp_error >=
0.05, `--tc 180+2,300+0`, Lichess, seven blocks 2024H2 → TREAT. Counts
reproduce the published table to the hit (93 / 51 / 183 / 46 / 28 / 196 / 92 =
689 over 18,370 eligible moves).

## Method

Stockfish 16, depth 18, one thread per search. Per hit: P0 (before his move:
best move, score, PV), P1 (after the move played), P2 (after the move played +
the flagged capture). Scores jamorgan-POV. Cross-check: the 196 hits whose
`FEN|move` is in `depth18_verify.json` reproduce it within 50cp on both sides
in 91% (median difference 10–11cp).

Material = 1/3/3/5/9 from his POV.
- `m0` = raw count before his move + best recapture on the square the opponent
  just captured on (a half-finished trade reads level; free material elsewhere
  is *not* credited, so taking a hung piece shows up as a gain).
- Line ends are "resolved": + best SEE capture for the side to move; mate = ±40.
- Horizon 6 plies including his move (three moves each), matching the
  visibility study. `HANG_HORIZON=16` changes no conclusion (shares move ≤ 3 pp;
  table below).
- `gain_best` = resolved material at the end of the best line − m0.
  `loss_play` = m0 − resolved material at the end of (played move + opponent's
  best line).
- `err18` = winprob(s0) − winprob(s1). `cap_ok` = s2 − s1 <= 100 (the flagged
  capture is within a pawn of the opponent's best reply).

Classes: `noise` err18 < 0.05; `hang` loss_play >= 2 and cap_ok; `other_loss`
loss_play >= 2, flagged capture not the right reply (usually something bigger:
mate threat, bigger capture); `missed_win` loss_play < 2 and gain_best >= 2;
`no_mat` neither.

## Results

| class | n | share | sustained deficit | opp took flagged piece next move | his score | median spend | right after opp gift (>= 10 pts) |
|---|---|---|---|---|---|---|---|
| hang (flag right) | 372 | 54.0% | 60.2% | 64.2% | 0.36 | 8s | 33% |
| other_loss | 71 | 10.3% | 69.0% | 25.4% | 0.40 | 8s | 41% |
| missed_win | 88 | 12.8% | 15.9% | 44.3% | 0.52 | 7s | 52% |
| no_mat | 116 | 16.8% | 19.0% | 35.3% | 0.57 | 8s | 26% |
| noise (not an error at d18) | 42 | 6.1% | 23.8% | 47.6% | 0.58 | 9s | 17% |
| all | 689 | | 46.3% | 51.8% | 0.44 | | |

Horizon 16: hang 53.0 / other_loss 12.0 / missed_win 15.5 / no_mat 13.4 /
noise 6.1.

"Sustained deficit" = in the actual game, resolved material vs m0 is <= −2 both
6 plies and 20 plies after the decision (or at game end if sooner).

- **Material really lost: 443 / 689 (64%).** By depth-12 severity: wp_error
  0.05–0.10 → 25% (35% noise); 0.10–0.20 → 49%; >= 0.20 → 86%.
- **Real hangs by shape** (n = 372): standing threat missed 63%, moved piece
  lands en prise 14%, defender moved / line opened 12%, losing trade on own
  capture square 10%.
- **Missed win** is rarely a free piece: the depth-18 best move was a simple
  capture with SEE >= 150 in 13 of 88. It is mostly a 2–3-move tactic, and half
  follow an opponent mistake. 118 of the 443 real losses *also* had a >= 2-pawn
  win available in the same position (56 of them right after an opponent
  mistake).
- **Punishment.** Real hangs that were taken at once: 239, score 0.29. Not
  taken at once: 133, score 0.49. Real hang with sustained deficit: score 0.16
  (n = 224); without: 0.68 (n = 148). Median s0 for hangs is +4.1, so these
  games started clearly won.
- **Spend** is flat across classes (7–9s median), consistent with "Three
  failure modes": not a clock problem.
- By label: `missed their threat` 53% hang, `hung it myself` 64% hang.

Per eligible move, descriptive only (not a test):

| block | flagged | confirmed hang | hang + other_loss |
|---|---|---|---|
| 2024H2 | 4.45% | 2.68% | 3.16% |
| Q1-2025 | 4.15% | 1.95% | 2.69% |
| Q2-2025 | 3.66% | 2.00% | 2.30% |
| Q3-2025 | 3.54% | 1.92% | 2.00% |
| Q4-2025 | 4.04% | 2.45% | 2.89% |
| 2026 | 3.55% | 1.79% | 2.18% |
| TREAT | 3.63% | 2.01% | 2.48% |

TREAT is not the minimum under the cleaned definition either.

## What it means

- The flag is right about two times in three, and nearly always (86%) when the
  drop is large. The low-severity tail is mostly something else.
- For drills: the real-hang set is ~370 positions, two-thirds standing
  threats. `missed_win` and `no_mat` positions are different exercises
  (tactics; judgment) and should not be drilled with a "can they take
  something?" prompt.
- Losing trades are 10% of real hangs, matching the 2026-10-14 ceiling.

## Side check: known opening repeats in the F block

`/home/claude/repeats.py` (scratch, not committed). Lines from "Opening errors
are almost never repeats", counted in 2026 (Jan–Aug) and TREAT:

| line | 2026: reached / bad | TREAT: reached / bad |
|---|---|---|
| Englund 1.d4 e5 2.Nf3 …Nc6 | 11 / 11 | **8 / 7** (last 2026-11-23) |
| Englund 4.e3 …Qb4+ | 12 / 1 | 4 / 0 |
| Englund trap 7.Nd5 Bxd2+ 8.Nxd2 …Qxe5 | 1 / 1 | 1 / 1 |
| 1.d4 e5 2.Bf4 (as White) | 45 / 2 | 34 / 0 |
| Panov 5.Nc3 …Bf5 | 2 / 1 | 1 / 0 |
| Advance 7.h3 …Bh5 | 5 / 1 | 0 / 0 |

Depth 22 after 1.d4 e5 2.Nf3: 2…e4 +0.38, 2…exd4 +0.10, 2…d6 −1.29, 2…Qe7
−1.39 (Black POV), 2…Nc6 not in the top four (best reply 3.d5). Only the
2.Nf3 line is still live.

## Caveats

- Depth 18, 6-ply material horizon. A deep tactic can land in `no_mat`;
  mutual-hang positions can be ambiguous between `hang` and `missed_win`.
  Spot-checked eight by hand; the classes match the boards, with one fuzzy
  `missed_win` (big eval drop, small material within 6 plies).
- "Resolved" material is a one-square SEE at the line end, same limitation as
  `hanging.py`.
- Scores are raw, not eval-matched; classes start from different evals
  (median s0: hang +4.1, missed_win +5.4, no_mat +3.2).
