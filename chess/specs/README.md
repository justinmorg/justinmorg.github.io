# specs/ — post-block exercise specs (not built)

Written 2026-11-11. Build specs for four card groups that replace group F
after the 900-game block closes. Rationale and the routine they teach, in
plain language: `chess/notes/2026-11-11-post-block-plan.md`. Read that first.

| file | group | what it is | build order |
|---|---|---|---|
| `W-walkthroughs.md` | W | worked examples of the move routine on stretches of his own games; read, not answered | 1 |
| `S-scan-ladder.md` | S | five-rung scan drill, engine-free keys; supersedes the README "Group S (proposed)" draft | 2 |
| `G-guided-playthrough.md` | G | "mock game": play through a real stretch move by move with a scaffold that fades | 3 |
| `K-conversion-playouts.md` | K | his own won endgames, played out against the Lichess computer | any time; independent |

**Do not build before the block end** (pre-registration amendment 2026-10-30:
no new practice method before the later of game 900 and the last F session).
**None of this is a test.** No outcome, no pre-specification, no interim-look
rule. In-page accuracy and time are practice feedback.

## Decisions for Justin before any build

Collected here so one conversation settles them. Defaults in brackets.

1. S answer entry: tap pieces/squares [default] or tap full moves. See S §3.
2. S threat rule: thresholds and what is excluded. See S §6. [as drafted]
3. W: which three stretches, from the candidate list the build session
   produces. See W §3.
4. G source games: own games from 2023–24 [default] or stronger players'
   games in his openings from the panel. See G §2.
5. Whether F self-tags (README: caught obvious/difficult; missed I see why /
   don't get it / misunderstood my move) carry over to S5 and G. [yes]
6. Page: same `chess-drills/index.html` [default] or a second page. The page
   is already ~630 KB.

## Conventions shared by all four

- **Engine-free keys.** Every answer key is computed with python-chess from
  legal moves, attack maps and `hanging.see` only. Stockfish may be used at
  build time to *select* positions and to refuse obviously broken ones; no
  verdict shown to the player depends on an eval. Each spec states what that
  costs.
- **Position sources**, in order of preference: games Justin has not drilled
  (`data/pending/` August batch; the treatment block once annotated; 2023–24
  blocks), then the 243 F card positions and the P set. 3+2 / 5+0 only.
  London / Caro / Englund in proportion to play; no opening-phase positions
  (own move ≥ 12) except in K.
- **Keys and storage.** New `localStorage` objects, one per group:
  `drills.scan.v1`, `drills.guided.v1`, `drills.keep.v1`. W stores only a
  "read" flag in `drills.walk.v1`. Card keys `S{rung}-{gid}-{ply}`,
  `W-{gid}-{ply}`, `G-{gid}-{ply}`, `K-{gid}-{ply}`; ply = first own move of
  the card. None collide with `drills.done.v1` (`1`..`21`, `A-`/`B-`…
  priority keys), `drills.forward.v1` (`F-`) or the R notes. No
  `class="drill"`, so the 260 counter and its reset never see them (group
  R/F precedent). `drills.forward.v1` is left in place, read-only.
- **Export.** Each group gets "Copy my results as JSON"; `fbackup.py` is
  generalized (or cloned) with the same superset check.
- **Generators.** One script per group (`build_walk.py`, `build_scan.py`,
  `build_guided.py`, `build_keep.py`), each replacing only its own
  marker-bracketed block; byte-identical on rerun; the existing three
  generators and the new ones must leave each other's output unchanged
  (`cmp` after cross-rebuild). Each hard-exits unless replaying every card
  from its first FEN in python-chess reproduces every stored position, as
  `build_forward.py` does.
- **Page.** Mobile first: one card at a time, board full width, tap targets
  ≥ 44 px, no hover-only information, no wide tables. Board orientation from
  Justin's side. Reuse the F board model (64-array, own
  castling/en-passant/promotion) and cross-check it against python-chess on
  every embedded position before commit.
- **Timing.** Every answer records milliseconds. Decisions over 60 s are
  flagged as distraction in the export, not dropped.
- **Register.** Card text is plain language (README "Explaining results").
  No centipawns on cards. Material is named: "a knight for a pawn".
- **Shared helper.** `chess/scripts/scanlib.py` (new): `checks(board)`,
  `captures(board)`, `loose(board, color)`, `delta(before, move)`,
  `threats(board)`, each returning plain lists, with unit tests in the
  `test_see.py` style. All four generators import it so one definition of
  "loose" and "threat" exists.

## Definitions (single source; the specs refer here)

- **Other side's moves** in a position where it is not their turn: computed
  on a null-move copy. Skipped when the side to move is in check.
- **Winning capture:** legal capture with `hanging.see` ≥ 150 (a piece or
  more, the F threshold). **Pawn-winning capture:** SEE 100–149; shown,
  labelled "a pawn", never required.
- **Loose piece** (non-pawn, non-king): no defender, or attacked by a piece
  of lower SEE value (N = B). Pinned defenders count as defenders (same
  blind spot as `scanlevel.py`; say so on the card when a defender is
  absolutely pinned, which python-chess can detect).
- **Delta of a move** (own move m from square a to square b):
  *lands* — every legal capture on b in the position after m, with SEE;
  *leaves* — own pieces and pawns whose defender set lost a (and did not
  regain it from b); *opens* — enemy sliders whose attack set gained an own
  piece because a was vacated; *exchange* — m was a capture and the best
  recapture on b has SEE ≥ 150.
- **Threat** (for side X in position P, X not necessarily to move): a legal
  non-capturing, non-checking move t by X such that, after t and a null move,
  X has (i) a capture with SEE ≥ 150 on a square where X had no SEE ≥ 150
  capture in P, or (ii) mate in one. Tagged *same-piece* if the capturing
  piece is the one that played t, else *different-piece*. Excluded on
  purpose: threats of check-forks needing a third move, threats to win a
  pawn, positional threats, and any threat whose first move simply loses the
  piece (t lands on a square where the opponent has an SEE ≥ 150 capture of
  it — filtered out as "not a real threat").

Measured on the 243 F cards (1,409 own-move positions), for sizing only:
checks median 1 per side (p90 3); legal captures median 3 per side (p90 5);
own loose pieces median 1 (p90 3); opponent threats after the own move
median 3 (p90 8, max 16) before the "simply loses the piece" filter, 86%
same-piece. First-hang cause, once per hung piece, n = 217: already
capturable before the move 48%, lands 22%, exchange 14%, leaves 8%, opens
4%, other 4%. Descriptive; card positions are the tail and carry ~10% label
error.
