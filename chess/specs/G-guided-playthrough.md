# Group G — guided play-through ("mock game")

Status: spec only, 2026-11-11. Shared conventions and definitions:
`specs/README.md`. Build after W and after S4 exists (it reuses `delta`).

## 1. Purpose

The bridge between cards and a real board. S drills the looks one at a time
on a position that is handed over. In a game nobody hands over anything: the
routine has to be started by the player, on every move, including the many
moves where it finds nothing. G is a stretch of a real game played through
one move at a time, where Justin chooses his own move each turn and the page
enforces the routine at first and then stops enforcing it.

Solitaire-chess format: after his choice is checked, the game continues with
the move that was actually played, so the stretch stays on the real game.

## 2. Source games (decision 4)

Default: his own games from the 2023–24 blocks (not remembered), own moves
roughly 12–26, 10–14 own moves per card, 3+2 / 5+0, mix of London, Caro and
Englund by play share; both results; no stretch where the side he plays is
already lost at the start (depth-12 eval in the PGN, selection only).

Alternative: games by stronger players who use his openings, from the
anonymized panel (`data/panel/`, `panelrep.py`). Benefit: the "move played"
shown after each choice is a better player's move. Cost: panel games are
depth-annotated only for selected players and months, and the positions are
less like his own. Could be a second deck later; not the first build.

Roughly 40 cards to start. A card takes most of a 10-minute window.

## 3. One turn

1. Opponent's move is played on the board.
2. **Scaffold** (see §4) asks some or none of the routine's steps.
3. He enters his move by tapping from-square and to-square (promotion
   picker; castling by king move). Any legal move is accepted.
4. **Safety verdict on his move, engine-free**, from the precomputed table
   (§5): "nothing to take", or the opponent's winning captures in the
   position his move creates, drawn on the board, with the delta class
   (lands / leaves / opens / exchange / was already there).
5. The move actually played in the game is shown ("the game went Rd1"), with
   its own safety verdict if it differs from his. No judgment of which move
   was better. If the played move was itself a hang, the card says so and
   continues anyway; those are real stretches.
6. Next turn from the real game position.

## 4. Scaffold levels

| level | before he may enter a move | time shown |
|---|---|---|
| **G1 full** | Step 1: tap what their move now attacks (or "nothing"). Step 2: tap my loose pieces. Then enter the move. Then, before the verdict: lands / leaves answer as in S4. | none |
| **G2 check only** | Nothing before the move. After entering it: lands / leaves. | elapsed |
| **G3 bare** | Nothing. Enter the move, see the verdict. | 30 s per move budget shown as a bar; nothing happens at zero |
| **G4 blitz pace** | As G3. | 10 s bar |

G1 answers are keyed (`captures`-new, `loose`, `delta`) and shown as
found / missed, but the per-card headline at every level is one number: **how
many of his chosen moves left something to take.** That is the thing a game
punishes, and it is the only figure comparable across levels.

Level is chosen per card by a selector that defaults to the lowest level at
which his last five cards were clean. He can override it. Fading the prompts
is the design: if the clean rate only holds while the page is asking, the
habit is not installed yet, and the page should say so in those words.

## 5. Precomputed safety table

For every position in every card and every legal own move there (median
~35), the build stores: the move (UCI), the opponent's winning captures
after it (square, capturer, SEE class), and the delta class. This keeps the
page free of move generation and SEE in JavaScript; the page only looks up
the tapped move and replays moves on the 64-array. Size estimate: 40 cards ×
12 positions × 35 moves ≈ 17k rows; store only non-clean rows plus the legal
move list, well under 300 KB.

Legal-move entry needs the legal list per position (also precomputed), so an
illegal tap is rejected without JS chess rules.

## 6. What the engine-free verdict cannot say, stated on the intro card

- It says whether his move leaves a piece to be taken. It does not say
  whether the move was good. A safe, pointless move gets "nothing to take".
- If a capture the key reports would actually lose for the opponent (a
  counter-capture elsewhere), the key still reports it. The card offers "I
  think that capture fails" and stores the flag; no engine adjudicates.
- Hangs of the opponent's that he could have taken are not reported at all
  in G1–G4 (H1 is null as a general pattern). Optional toggle, off by
  default: after the verdict, list his own winning captures that were
  available, as information.

## 7. Self-tags (decision 5)

On any turn where his move left something to take, one tap: *I see why* /
*I don't get it* / *I meant a different move*. On the summary screen, the
reminder Justin asked for on F: do not sweat mistakes, the target is quick
vision. Tags are stored and exported; "I don't get it" positions are listed
at the end of the export for a later conversation.

## 8. Out of scope

Move-quality scoring. Opening moves. Playing on from his own chosen move
(would need an engine opponent; that is what correspondence games and spec K
are for). Any rating or streak.

## 9. Done when

Safety table reproduces from a clean clone byte-identically; every stored
legal-move list equals python-chess's; ten cards playable end to end on a
phone at G1 and G3; export and backup round-trip; cross-rebuild `cmp`
passes.
