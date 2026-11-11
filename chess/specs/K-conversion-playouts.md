# Group K — keep the win: conversion play-outs

Status: spec only, 2026-11-11. Shared conventions: `specs/README.md`.
Independent of W/S/G; small build.

## 1. Purpose

README "Where study time should pay off" ranks converting won endgames
first, and "Two regimes" shows that in clearly winning positions most large
drops are quiet moves never punished by a capture. No scan drill touches
that. Justin has never studied endgames. The README plan answers with
videos and rewatching; this adds the active half: play his own won positions
out against a computer until they are won.

The engine here is a sparring partner, not an answer key.

## 2. Format

A card is one position from his own games with a link that opens Lichess
"play with the computer" from that position, his colour, a suggested level
and no clock. He plays it out in the Lichess app, comes back, and taps one
of: *won / drew / lost / gave up*, plus an optional one-line note. Second
and later attempts at the same card are stored as a list.

Link form to verify at build time against current Lichess behaviour:
`https://lichess.org/?fen=<url-encoded FEN>#ai`. If that no longer opens the
dialog pre-filled, fall back to `https://lichess.org/editor/<FEN>` with a
one-line instruction ("Continue from here → Play with the machine").

Card text, plain: material in words ("rook and four pawns against rook and
three"), whose move, how the real game ended, and nothing else. No eval, no
hint.

## 3. Decks

Selection uses the depth-12 evals in the annotated PGNs (selection only) and
`features.py` game columns.

| deck | positions | size | suggested computer level |
|---|---|---|---|
| **K1 small edge** | endgame entry at +1 to +3 pawns (the 53.2% bucket), games he did not win first | ~40 | start 4; raise when he wins three in a row |
| **K2 should be over** | endgame entry or late middlegame at +3 to +6, not won in the game | ~40 | start 5 |
| **K3 by type** | from K1/K2, grouped: rook endings, minor-piece endings, queen endings, pure pawn endings | tags on the same cards, not new ones | — |

K3 tags let a play-out window follow a video sitting on the same ending
type. Rook endings first: most common in practice, and the README plan
names them.

Exclude positions where the stored eval is contradicted at depth 18 (README
"Individual evals can also just be wrong") and anything with a forced mate
in under five.

The existing 21 endgame drills (`drills.done.v1` keys `1`–`21`) stay as
they are. If any coincide with K positions, link them rather than duplicate.

## 4. Feedback

Per deck: attempts, won share on first attempt, won share on latest attempt.
That is all. A position lost twice gets a "watch it back" link to the
Lichess analysis board for the original game at that move.

## 5. Out of scope

Theoretical positions and tablebase drills (a book or video does those
better). Any scoring of individual moves. Clocked play-outs, at least at
first: the gap being trained is knowing what to do, and the clock result
from README "Resignations and flags" is a separate matter.

## 6. Done when

Links open a playable game from the right position and colour on his phone;
80 cards across K1/K2 with K3 tags; results store, export and back up;
cross-rebuild `cmp` passes.
