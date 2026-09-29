# Discussion notes: the group F "hangs" label is misattributing errors

Written 2026-09-29, for picking up in a later session. Plain-language companion
to the README section "Known mislabels found during the frozen block", which
has the engine lines and numbers. Read that section too.

## What happened

Two cards in a row turned out to be marked wrong, both found by Justin while
playing them:

- **Card 33** (`F-QMTTIZzN-36`), decision 5, 18...Ne4. Marked "hangs." It
  doesn't: 19.fxe4 loses White's queen to ...Bxe2. The move did cost about
  four-fifths of a pawn, but through a knight trade that wins White a pawn,
  which is below the drill's piece threshold.
- **Card 34** (`F-fhmnBsNB-56`), decisions 3 and 4, 27...Rc2 and 28...Rxc3.
  Both marked "hangs," while decision 2 (26...Rxc1), with the same exposed
  bishop on g5, was marked safe. In all three, Nxg5 wins White nothing,
  because a rook takes the queen or wins the queen trade. What 3 and 4 have
  in common is a **missed win**: 27...dxe4 (a free knight) and 28...Rxd2
  (takes the queen).

## The underlying problem, in one sentence

The labeller calls a move "hangs" when (a) something of Justin's worth a piece
can be captured and (b) the move was noticeably worse than the best move. It
never checks that (a) is the *reason* for (b).

So whenever something was capturable, "safe" quietly meant "you played the
best move," which is not what the drill asks. Justin's reading is the intended
one: safe means you didn't leave a piece to be taken for nothing, not that you
found the best move.

This is a different bug from the September 3 label audit. That one was a
*wrong engine number*. This one has the *right number with the wrong
explanation*, which is why the depth-18 recheck could not catch it: the recheck
only confirms that the eval dropped.

## What we agreed

- **No card changes until the treatment block is done.** The frozen-scope rule
  holds: any change restarts the block. The in-page score is practice feedback,
  not the outcome, so wrong labels cost nothing that matters for the test.
- **After the block closes:** deep-check (depth 18+) every decision Justin got
  "wrong" in the `drills.forward.v1` export, in both directions. This is for
  learning and doubles as a cheap label audit. Limitation: a bad label he
  happened to agree with won't surface this way.
- **Fix for the next card set:** for a "hangs" label, actually play the flagged
  capture and check that it wins at least a piece's worth of material by force.
  If it doesn't, label it compensated (safe).

## Open questions to discuss

1. **How big is this?** Two cards found by chance, out of ~40 played so far,
   is suggestive, not a rate. After the block, measure it on all 256 "hangs"
   steps with the play-the-capture check. That's minutes of engine time.
2. **Does it touch the pre-registered outcome?** Yes, partly. `hanging.py` uses
   the same one-square check, so some counted "hits" in every block are this
   kind of false alarm. Card 34's anchor move is one of them. The working
   assumption is that it inflates every block by about the same amount, so the
   before/after comparison survives, the same argument used for the floor
   change. That assumption is untested. Decide whether to measure it on the
   baseline blocks *before* the treatment block is tested, so the answer can't
   be shaped by the result.
3. **Should the next card set give the right answer on "missed a better move"
   decisions?** Possibly say "safe, but there was a stronger move: dxe4 wins a
   knight." That would keep the drill honest about its one question and still
   teach the missed win.
4. **Floor sensitivity.** Card 34's decisions 3 and 4 fall below the 0.05
   win-probability floor at depth 22 but above it at depth 18. How many hits
   sit this close to the floor, and does it matter?
5. **The chess lesson from card 34.** The real miss was White's knight on e4,
   attackable by the d5 pawn two moves running. The README records "missed own
   resource" (H1) as testing null *as a general pattern*. That doesn't stop an
   individual card from being a clear example of it. Worth keeping the two
   ideas separate in conversation.
