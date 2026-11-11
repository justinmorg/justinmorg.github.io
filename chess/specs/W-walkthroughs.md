# Group W — worked walkthroughs of the move routine

Status: spec only, 2026-11-11. Shared conventions and definitions:
`specs/README.md`. Origin: Justin, 2026-10-27 — a card-page walkthrough of a
Heisman-style thought process on a few consecutive moves of a real game,
because he does not know what to do with thinking time and doubts he can hold
a whole process in his head.

## 1. Purpose

Show the four-step slow routine and the two-look blitz routine being run,
move after move, on positions from his own games, before he is asked to run
them himself (S, G). Read-only: no answers, no score. A worked example comes
before a drill.

## 2. Format

One walkthrough = 6–8 consecutive own moves of one game. One own move per
screen. Each screen reveals in order, one tap each:

1. **Their move.** Board with the opponent's last move highlighted. Text:
   what it now attacks (new captures available to them, from `captures` on
   the null-move copy, minus those available one ply earlier), what it stopped
   guarding, and the pass question answered: "if they moved again: …" (top
   threat by SEE gain from `threats`; "nothing that wins a piece" is a common
   and deliberate answer).
2. **Inventory.** My loose pieces highlighted in one colour, theirs in
   another (`loose`). One line each.
3. **Candidates.** My checks and winning captures listed (`checks`,
   `captures`). Then the move actually played, with one sentence on its idea.
   No claim that it was best. Where an obviously natural alternative exists,
   name one ("Rd1 does the same job") in the chessbrah manner: several moves
   are fine, here is what matters.
4. **Safety check on the played move.** Lands / leaves / opens from `delta`,
   drawn as arrows on the *pre-move* board first (as at the board), then the
   move is made and the opponent's checks and winning captures in the new
   position are shown. Verdict line: "nothing to take" or "this leaves the
   bishop on g5 to the knight".
5. **Blitz version of this move**, one line: what Look 1 and Look 2 would
   each have said. On most moves both say "nothing". That is the point: the
   routine is usually ten seconds of nothing.

A final screen per walkthrough: the two or three moves where the routine
mattered, and which step caught them.

## 3. The three walkthroughs

Selected by the build session and offered to Justin as a short candidate
list (five or six), three chosen:

- **W1, nothing goes wrong.** A winning or level middlegame stretch, moves
  roughly 13–22, London as White, in which the opponent makes at least two
  real threats (per the definition) and each is met. Teaches that the routine
  returns "safe" most of the time.
- **W2, the move creates the hang.** A stretch containing one hang whose
  cause class is *lands* or *leaves*. Preferably a Caro game.
- **W3, the stale one.** A stretch where a piece becomes capturable, is not
  dealt with, and is taken two or three moves later (cause class "already
  capturable", `std` = 1 in F terms). Step 1 on the later screens repeats
  the same unanswered item so the staleness is visible on the page.

Optional fourth, only if he wants it: a winning position that drifts with no
capture ever punishing it (the +350 band in README "Two regimes"), to show
what the routine does *not* catch and where step 3's "ahead: trade pieces"
does the work.

Use games old enough not to be remembered, and not F card windows he has
already played.

## 4. Text authoring

The lists and arrows are computed. The one-sentence "idea" lines in step 3
and the closing screen are written by the build session, by hand, per move,
under two constraints: (a) every factual statement about attacks, defenders
and captures must match the computed lists, and the generator asserts this
for any square named in the text via a small tag syntax, e.g.
`{att:g5<e4}` must be true in the position or the build exits; (b) no
evaluation words that need an engine ("winning", "best", "blunder") except
in W2/W3 for the single hang move, where the capture itself is on the board.

Stockfish is used once, at selection, to refuse a stretch in which the
played moves include an unrelated large drop that the commentary would have
to ignore.

## 5. Out of scope

No quiz elements (that is S and G). No opening theory. No endgames (K). No
video or animation beyond move-by-move reveal.

## 6. Done when

Three walkthroughs render on a phone, every tagged assertion passes, the JS
board matches python-chess on every position, and Justin has read one and
said whether the density per screen is right before the other two are
written.
