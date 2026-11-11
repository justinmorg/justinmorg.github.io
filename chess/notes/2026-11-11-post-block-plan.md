# After the 900-game block: plan review

Written 2026-11-11 at Justin's request. Plain-language companion to the README
section "After the treatment block: plans, not tests". The goal set for this
review: do what is most likely to make him better at chess generally. No new
test, no significance threshold. Build specs for the exercises proposed here
are in `chess/specs/`; nothing in them is built yet.

**Nothing below starts until the block closes** (900th game or last F session,
whichever is later). That includes trying the move routine in games.

## The short version

The README plan is sound and should mostly stay. Three changes:

1. **Practise the move routine at a real board, not only on cards.** The plan
   lists slower games as "when time allows". They should be a core item,
   because every strong result in this project points at the same thing: the
   safety look does not fire during a game. Cards rehearse the look; only games
   rehearse firing it. The obstacle was that a slow game does not fit a
   10-minute window. Correspondence games (one day per move on Lichess) do:
   open the app, run the whole routine on one or two moves, close it.
2. **Make the endgame work active.** Videos alone are the weakest way to learn
   a skill. Pair each video sitting with playing out his own won endgames
   against the Lichess computer (spec K).
3. **Reshape group S.** As drafted it asks for every check and every capture
   for both sides, scored on completeness. That builds board sight, which is
   worth a little, but its end point is a list, and a list is not what gets
   used in a game. The reshaped ladder ends at a two-look check small enough
   for blitz, and is preceded by worked examples and followed by a guided
   play-through of real game stretches (specs W, S, G).

## The routine being taught

Two versions of one thing. The slow version is for correspondence games,
cards and any game with real time. The blitz version is what is left when the
slow version has been done often enough to shrink.

**Slow version, four steps.**

1. *Their move.* What does it attack now, and what did it stop guarding or
   unblock? Then the "threat" question: if they moved again right now, what
   would they do?
2. *Inventory.* Which of my pieces are loose: undefended, or attacked by
   something cheaper. Same for theirs.
3. *Candidates.* My checks, captures and threats first, then quiet moves. No
   idea at all: improve the worst-placed piece. Ahead in material: trade
   pieces, not pawns.
4. *Safety check on the move chosen, before playing it.* Where does the piece
   **land** (can it be taken there, and by what)? What does it **leave**
   (what was it guarding or blocking)? Then their checks and captures in the
   new position. If something fails, back to step 3.

**Blitz version, two looks.**

- *Look 1, when they move:* what of mine can they take right now?
- *Look 2, move chosen, hand not yet moved:* lands, leaves.

Count attackers against defenders only when a piece is attacked and both
looks come up otherwise clean. The scan-level table says three hangs in four
need no counting.

Why two looks and not one. Sorting the hang moves on the current F cards by
what caused them (once per hung piece, 217 cases, computed from the board
alone, no engine):

| what happened | share |
|---|---|
| the piece could already be taken before my move, and I played something else | 48% |
| the piece I moved landed where it could be taken | 22% |
| I captured, and lost the exchange on that square | 14% |
| the piece I moved had been guarding the thing that got taken | 8% |
| my move opened a line for their attacker | 4% |
| other (pins, counting) | 4% |

So about half are visible on the board as it stands, with nothing to
visualise. That is Look 1, and it is the target-first idea Justin raised on
2026-10-30. The other half are created by the move, and "lands, leaves" covers
most of them. Caveats: these are card positions, which are the costly tail of
his games, about one label in ten is known to be wrong, and this is a
description for designing a drill, not a finding.

## On "threats"

Justin has said he does not know how to check for threats and that when he
imagines the opponent moving twice he only sees the same piece moving twice.
Two things from the card positions (313 sampled, mechanical rule, no engine):

- A typical position has about three opponent two-move ideas that would win a
  piece if ignored; one position in ten has eight or more. So "find all
  threats" is not a sensible ask. "Find the biggest one" is.
- In 86% of them the piece that moves first is also the piece that captures.
  So the same-piece habit already covers most threats. The gap is the other
  14%: one piece moves and a *different* piece captures (a line opens, a
  defender is driven off or pinned). That is a narrow, nameable thing to
  drill, and spec S gives it its own deck.

## What a week looks like

Not a schedule. A sense of proportion for the 10-minute windows.

- **Blitz** stays the largest share. It is the part he enjoys. One rule only
  during blitz: the two looks. Nothing else from this document is attempted at
  3+2.
- **Two or three correspondence games running at once.** The slow routine,
  written out for the first couple of weeks if that helps. No analysis board
  at first: the point is to picture the position after the move.
- **Four or five windows of cards**, in the order W (examples, read once), then
  the S ladder, then G (guided play-through). S and G replace group F.
- **Endgames: two video sittings and two play-out windows.** Rewatching is the
  method, as in the README. The play-outs come from his own games.
- **One loss a day, three minutes.** Find the turning point before opening the
  engine, then name which look would have caught it: Look 1, Look 2, or
  neither. "Neither" positions are the ones worth saving. No spreadsheet.
- **The opening patch, one evening, once.** The repeat lines already listed in
  the README.
- **An occasional 15+10 game** when there is a free half hour.

## What I would not do

- Try to run full checks, captures and threats on every blitz move. It does
  not fit, and Justin has said so. The two looks are the blitz version.
- Score the new cards against an engine. The keys in the specs are computed
  from the rules of chess alone, which is what he asked for. The cost is
  stated in each spec: a capture the key calls "available" is sometimes a bad
  capture, and the card will not know.
- Turn any of this into a measurement. The card pages will show accuracy and
  time as practice feedback. The hang rate will get looked at whenever games
  are next pulled for some other reason, and not before.
- Expect scanning to fix the won-position problem. In clearly winning
  positions most of his big drops are quiet moves that are never punished by
  a capture at all. That is a conversion skill. Spec K and the endgame work
  are aimed at it; the scan cards are not.

## One loose end in the README

The pre-registration says that if the F test is null, the next step (slow
games with the single instruction to run the check) "would be pre-registered
the same way". Justin has since decided against any further formal test.
The slow-game idea stands; the pre-registration of it does not. Recorded in
the README next to the pointer to this note so a future session does not
treat it as an obligation.

## Closing out F first

One session after the 900th game: pull the games, confirm the 900 by
timestamp, annotate, run the test once and report it as the README says
(including the partial-dose wording). Then the deep check of every card
decision he got "wrong", which is where the label fixes come from. After that
the F cards are retired and their positions feed S.
