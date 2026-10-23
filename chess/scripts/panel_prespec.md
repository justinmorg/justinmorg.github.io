# Pre-spec: thread 9 — how do improvers improve? (improvers vs controls)

**Agreed 2026-10-23, committed before step 2 (panel selection) ran.**
Written while the step-1 header index of Sep 2025 and Sep 2026 was still
streaming, so before the panel existed and before any game in it was
annotated. Nothing in step 2 looks at an outcome metric, but the selection
rules are part of the test, so they were fixed first. Every choice below was
settled by Justin on 2026-10-23; earlier drafts are in git history.

## Question

Among Lichess players in roughly Justin's range who gained a lot of rating
between Sep 2025 and Sep 2026, did the gain come from

- **H-all** — improving every area by about the same amount,
- **H-strength** — improving most in the area that was already their best, or
- **H-weakness** — improving most in the area that was their worst?

"Area" is a position bucket; "best" and "worst" are judged against same-rated
peers, not against 50% or against each other's raw rates (see Profile). The
comparison is always improvers **minus matched controls**, because a year of
play, rating-pool drift and regression to the mean all move these numbers in
players who did not improve.

## Scope and exclusions

- Source: Lichess open database, `standard_rated_2025-09` and `_2026-09`,
  via `panel_index.sh` (step 1) and the step-3 extract pass.
- Qualifying game: `Event` starts `Rated Blitz`, **non-arena**
  (`arena = 0`; berserk halves the clock), `TimeControl` 180+2 or 300+0 (the
  corpus default), `Termination` not `Abandoned` / `Rules infraction`.
- **`jamorgan` is excluded from every step.** His Sep 2026 games are group F
  treatment-block games; computing any bucket rate on them would be an interim
  look. His rows stay in the raw index (headers only) and are dropped at
  selection, before anything else touches them.
- Accounts flagged by `lichess.org/api/user/<name>` as `tosViolation`,
  `disabled` (closed) or titled `BOT` are excluded at selection. This matters
  most for improvers: a +150 jump is exactly where undetected engine use
  concentrates, and the flag is the only check available.

## Panel selection (step 2)

Per player-month, from the index: qualifying games `n`, and **monthly mean
rating** = mean of the player's own pre-game rating across those games.

1. Eligible: `n >= 150` in **both** months; Sep 2025 mean in **1150–1750**.
2. `gain` = Sep 2026 mean − Sep 2025 mean.
   **Improver**: `+150 <= gain <= +300` (decided 2026-10-23). **Control**:
   `|gain| <= 50`. Others dropped. +150 is large enough that luck alone
   rarely produces it at 150+ games a month; the +300 cap keeps out gains no
   adult in this range plausibly makes in a year, which are more likely
   returning or sandbagged accounts, or engine use, than improvement.
3. Persistence gate, improvers only: current blitz rating from the user API
   (late Oct 2026) must be `>= Sep 2025 mean + 100`. Guards against Sep 2026
   being a lucky month. There is deliberately **no** matching check that Sep
   2025 was not an unlucky month (decided 2026-10-23: no Aug 2025 pass; the
   `rating-history` endpoint returns empty anonymously). That residual is
   listed under Hazards.
4. Matching: in random order (seed 23), each improver takes the unused control
   with the nearest Sep 2025 mean rating, within ±30, whose Sep 2025 `n` is
   within a factor of 2. Improvers with no match are dropped. All matched
   pairs are then put in one **random rank order (seed 23)**, fixed and
   committed (as anonymous ids) before any annotation.
5. Target **40 pairs** (decided 2026-10-23): ranks 1–40 are annotated
   (80 players, 160 player-months; ~15 h of engine time at ~5–6 min per
   player-month, so 3–4 sessions).
   - **Replacement.** A pair that fails the area rule below is replaced by
     the next unused rank. Allowed because the rule depends only on move
     counts per bucket, never on an error rate.
   - **One pre-declared extension.** If the 40-pair result is *unresolved*
     (Decision rule), and enough ranked pairs remain, ranks 41–80 are
     annotated and the test is run once more on all 80. To pay for two
     looks, each look uses alpha **0.029** in place of 0.05 (Pocock, two
     looks), for the gate and for β. No third look, and no extension after a
     resolved result.
6. Games per player-month are capped at **250**, sampled at random (seed 23)
   if over, so heavy players don't eat the engine budget.

Selection uses only ratings, counts and account flags.

**Pseudonyms.** Each username becomes `P` + the first 10 hex characters of
HMAC-SHA256(secret, lowercased username). The 32-byte secret is generated
once, handed to Justin as a file to keep locally, and never committed. Two
ways back to a name, so more games can be pulled later:

- the **key file** handed over alongside the secret (id → username, as a CSV),
  which Justin keeps locally; pasting it into a future session is enough;
- or, with only the secret: re-hash every name in any index file (or any
  later database month) and match ids. The hash does not reverse on its own;
  it needs the candidate list, which the database supplies.

The repo only ever holds ids. Neither file, nor the index, is committed.

## Areas

Six of the ten `buckets_prespec.md` buckets, unchanged definitions:
**Opening, MG level, MG winning, EG ahead, EG level, M2 mate danger.**

Left out: M3 (cannot err), MG losing and EG behind (little win chance left to
lose; rates ~2–3.5%, too flat to rank), M1 (too few moves per player-month).
Set agreed 2026-10-23. An area counts for a player only if it has **>= 100
own moves in every half-month it is measured on** (below); a player needs
**>= 5** counting areas or is dropped, and a dropped player takes their pair
with them, replaced from the rank list (Panel selection, step 5). The thin
areas are M2 and the endgame buckets, and the players at risk are those near
the 150-game floor (~75 games per half). Attrition is reported: how many
ranks were consumed to fill 40 pairs, and which area failed. If more than
**half** the pairs examined fail, the rule is too tight for this pool and
the run stops for a decision rather than continuing to consume ranks.

## Metric

Per player, area, measurement unit: P1 error rate (`wp_error >= 0.15`, same
curve as the bucket tables) on own moves, put on the **log-odds** scale:
`L = logit((errors + 0.5) / (moves + 1))`. Log-odds because the areas sit at
very different base rates (opening ~4%, MG level ~13%) and a point off 4% is
not the same thing as a point off 13%.

Pipeline per player-month as in the bucket run: `annot_inc.py` (depth 12,
server evals overwritten), `features.py --emit-fens all` with the player's
anonymous id as the user, `matedanger.py`, then bucket assignment exactly as
`buckets.py`.

## Profile, and the regression-to-the-mean trap

If best and worst areas are picked from the same Sep 2025 games that the
change is measured from, the worst area will appear to improve and the best
to decline in every group, by noise alone. Controls share that artifact, but
it inflates variance and it is avoidable. So:

- Each player's Sep 2025 games are split by game order into **half A** (odd)
  and **half B** (even).
- **Profile on A.** Per area, fit across all panel players a weighted linear
  fit of `L_A` on Sep 2025 mean rating (weights = moves). Relative strength
  `R_a` = player's `L_A` minus the fit. Lowest `R` = **best** area, highest =
  **worst**.
- **Change on B.** `I_a = L_B(Sep 2025) − L(Sep 2026)`. Positive `I` = fewer
  errors = improved.
- **Cross-fit**: repeat with A and B swapped and average each player's
  statistics over the two directions.

## Statistics

Per player:

- **β** (primary): slope of `I_a` on `R_a` across that player's counting
  areas. β > 0: weaker areas improved more (H-weakness). β < 0: stronger
  areas improved more (H-strength). β ≈ 0: no tilt.
- **C** (plain-language companion): `I_worst − I_best`.
- `I_all`: mean `I_a` over counting areas.

Group excess = improver mean − control mean, for each of β, C, `I_all`, and
`I_a` per area. Inference: sign-flip permutation of within-pair differences,
20,000 draws, seed 23, two-sided; 95% intervals by pair bootstrap, 2,000
resamples, seed 23.

## Decision rule

First, a **gate**: excess `I_all` must be > 0 at p < 0.029 (the per-look alpha; see the extension rule). If improvers did
not make fewer errors than controls on this measure, the panel cannot say
*how* they improved, and the result is reported as "rating gain not visible
in error rates" — itself worth knowing — with nothing below interpreted.

Then, on excess β (the primary, one test, alpha 0.029):

- **H-weakness**: excess β > 0, p < 0.029, **and** excess C > 0.
- **H-strength**: excess β < 0, p < 0.029, **and** excess C < 0.
- **H-all**: excess β not significant, its 95% interval within **±δ**, and
  excess `I_a` > 0 in at least 4 of the counting areas. δ = **0.5**
  (agreed 2026-10-23; a slope of 0.5 means an area one log-odds unit weaker than
  peers improved half a unit more).
- Anything else — e.g. β not significant but its interval too wide to rule
  out a tilt — is **unresolved**, and is reported as such with its interval.
  This is the likely outcome if the effect is a mild tilt (Resolution).

If β and C disagree in sign the result is unresolved regardless of p.

## Secondary (reported, no decision rides on them)

- **Per-area excess `I_a`**, Holm across six. This catches a fourth pattern
  the three hypotheses miss: everyone improves the *same* area whatever their
  profile (e.g. MG level). That would show as β ≈ 0 with one area carrying
  the gain, and would fail the H-all rule.
- Composition: per-area mean `cp_before` and move share, both months, both
  groups. If an improver's MG-winning rate falls because their winning
  positions got more winning, that is composition, not skill — checked the
  way the bucket run did, by eval-band standardization, post hoc and labelled.
- 3+2-only robustness: β excess must share the sign.
- **Repertoire change** (Justin's hypothesis, 2026-10-23): a player who
  switches openings may err more in the opening at first, lose rating, then
  recover it as the new lines settle. That player would be selected as an
  improver, show opening as their Sep 2025 worst area, and look like
  H-weakness — when it is a recovery, not improvement. Two pre-declared
  checks, from the extract pass's `ECO` tags, neither of which can be
  tuned after the outcome is seen:
  - *Repertoire overlap* per player: share of games, by colour, whose
    opening family (first ECO letter + two digits, as `openings.py` groups
    them) appears in both months, weighted by frequency. Reported for both
    groups; a gap between groups is itself a finding.
  - *Sensitivity*: the primary β test rerun with every pair dropped in which
    either player's overlap is in the bottom 20% of the panel. If the
    verdict changes, the write-up says so and leads with it.
  - Players whose Sep 2025 opening `R` is in the panel's top 10% are listed
    by id for a look in chat (the key file recovers the name; their games
    can then be pulled from the database or Lichess).
- Where Justin's own Sep 2025 profile (from the committed Q3 2025 block,
  which predates the drill) would rank him — descriptive, one line.

## Resolution, estimated now

From the README's ±2 pts per bucket at 150–300 games: at a ~10% base rate
that is ~0.2 log-odds per area per player-month, ~0.3 on a half-month. A
per-player change carries three such terms after cross-fitting; with
between-player variation on top, the excess `I_a` per area resolves roughly
**±0.15–0.2 log-odds at 40 pairs** (about ±1.5–2 pts at 10%), and excess β
roughly **±0.4**. At 80 pairs (the extension) both shrink by about 30%:
±0.1–0.14 per area, ±0.28 on β — after the stricter 0.029 alpha, a
real but modest sharpening, not a different instrument.

For scale: in Justin's own opponent-quartile table, ~190 rating points
separates the bottom and top quartile by ~0.15–0.25 log-odds in opening,
MG level and EG level. So a +150 gain should be visible as a pooled
`I_all`, a gain concentrated in one area (several times the average there)
would be clearly visible, and a mild tilt — worst area improving, say, 1.5
times the average — would not be. Stated now so an "unresolved" is read as
"too fine to see", not "no tilt".

## Hazards, stated

- Selecting on rating gain partly selects on luck; the threshold, monthly
  means, persistence gate and controls are the mitigations, not a cure.
- No check that Sep 2025 was an unlucky month for improvers (no Aug 2025
  pass, by decision). The split-half profile removes the noise artifact in
  best/worst picking, and controls absorb ordinary regression, but an
  improver who was *temporarily* below their level in Sep 2025 (a slump, a
  new opening) is not distinguished from one who really improved. The
  repertoire checks above cover the opening case only.
- The `n >= 150` rule over-represents heavy players; results describe heavy
  blitz players in this range, of which Justin is one.
- Undetected engine use among improvers would show as implausibly large,
  uniform `I_a`. Any improver whose Sep 2026 P1 rate is below the panel's
  minimum in **every** area is listed (not dropped) in the write-up.
- Depth 12 is reliable at the +150/±100 bucket lines and the 15-point P1
  line; nothing here leans on +5.

## Not affected

The group F pre-registration is untouched: `jamorgan` is excluded at step 2
and no game of his dated after the F start is read by any step.
