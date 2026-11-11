# Group S — the scan ladder

Status: spec only, 2026-11-11. Supersedes README "Group S (proposed):
engine-free scan ladder" (2026-10-26). Shared conventions and definitions:
`specs/README.md`. Origin: Justin, 2026-10-26 and 2026-10-30 — staged
checks → captures → threats on his own card positions, engine-free keys,
select the issues rather than answer safe/hangs, target-first threat scan.

## 1. What changed from the README draft, and why

The draft's three passes (all checks; checks and captures; checks, captures
and threats; both sides; completeness-scored) are kept as the first rungs but
are no longer the destination. Reasons:

- The end product of the draft is a complete list. What a game needs is the
  two-look check in the plan note. The ladder now ends there.
- "All threats" is not a feasible ask: median 3 and up to 16 per position
  under the mechanical rule. The threat rung asks for the biggest one.
- About half of first hangs on the F cards were capturable before the move.
  A target-first rung (my loose pieces, on the board as it stands) is added;
  it needs no visualization and was Justin's own proposal.
- The move-created half is mostly "lands" and "exchange" (36 of 52 points).
  A delta rung drills exactly that.

## 2. Rungs

Each rung is its own deck over the shared position pool. Opponent's side is
asked first and weighted (H2; README "The forcing layer").

| rung | board shown | ask | key |
|---|---|---|---|
| **S1 checks** | current position | "Tap every piece of theirs that can give check. Then yours." | pieces with ≥1 legal checking move, each side |
| **S2 takes** | current position | "Tap every piece of yours they can capture." Then, per tapped piece, one of: *free / they win material / fair trade or defended*. Then the same for their pieces. | capturable squares; class from SEE: ≥150 "win material" (sub-label free if no defender), 100–149 "a pawn", else "fair or defended" |
| **S3 loose** | current position | "Tap every loose piece of yours." (undefended, or attacked by something cheaper). Theirs second. | `loose` |
| **S4 lands / leaves** | pre-move position; own move **named, not shown** (F convention) | Three taps: can the moved piece be taken where it lands (no / yes, fair / yes, loses material); tap anything it was guarding that is now short a defender; tap any enemy piece that now sees through the vacated square. | `delta` |
| **S5 two in a row** | current position, opponent to move twice | "They get two moves. Find the pair that wins the most." Tap the piece that moves first, then its destination. "Nothing wins a piece" is a button. | `threats`, ranked by SEE gain; any listed threat scores as found, the top one scores as best |
| **S6 the two looks** | F-style window of 4–7 consecutive own moves, move named not shown | Per move: Look 1 — tap what they can take right now (or "nothing"); move is named; Look 2 — lands / leaves as S4 collapsed to "fine" or tap the problem. | union of S2 winning captures before the move and `delta` after |

S6 is the replacement for group F. It differs from F in three ways: the
answer is a tapped square, not safe/hangs; the key has no eval term, so the
C class and the mislabel class in README "Known mislabels" cannot occur; and
Look 1 is asked before the move is named.

**S5 sub-deck, "different piece".** Positions whose top threat is tagged
different-piece only, with one fixed hint line: "the piece that captures is
not the piece that moves first." This is the 14% Justin says he cannot
picture. Start it only after plain S5 is comfortable.

## 3. Answer entry (decision 1)

Default: tap pieces and squares, never full moves, except the S5
destination. A piece-level key is exact, fast on a phone, and matches the
target-first habit. Cost: "the rook can give check" does not show he saw
which check. The reveal therefore draws every move behind each keyed piece
as arrows, hit or miss.

Alternative: tap from-square then to-square for every move. Exact at move
level, roughly three times the taps. Not recommended for S1–S3.

## 4. Scoring and feedback

- Per card: found / keyed, plus false taps. Shown as "found 3 of 4, one
  extra", never a percentage. Misses are redrawn on the board in a second
  colour.
- Per rung, in the stats line: last 20 cards' found share and median time.
- **Par time** per rung appears after the first 30 cards on that rung, set to
  his own median; the display then shows time against par. Loose timing
  first, compress later (README draft, kept).
- Suggested move-up point, a hunch and not a gate: 9 in 10 cards complete
  with no extras over two sittings. He can skip rungs at will.
- S1–S3 are warm-ups. Expect a week or two there, not months. If S1 is
  trivially easy on day one, drop it.

## 5. Decoys and base rates

- S2–S4: no decoys needed; the key is a set and is often small or empty
  ("nothing to tap" is a button and is the key on a real share of cards).
- S5: at least 40% of cards have no listed threat.
- S6: window construction as F (3–5 own moves before a hang, 0–2 after,
  seeded from game id) but hangs are defined by the SEE key alone; 25% decoy
  windows with empty keys throughout.

## 6. The threat rule (decision 2)

As in `specs/README.md` Definitions. Known limits to state on the S5 intro
card, in plain words:

- It finds two-move wins of a piece and mates in two moves by the same
  side. It does not find forks that start with a check (those are checks,
  S1), pawn wins, or anything positional.
- SEE treats a pinned or overloaded defender as a real defender, so some
  real threats are missing from the key and a correct tap can be marked
  extra. The card offers "I think the key is wrong" (stored in the export)
  on every reveal, the F lesson from cards 33/34/130.
- A keyed threat may be easy to parry. The ask is "what would they do with
  two moves", not "is this dangerous".

Before building: run the rule over the pool and hand-check 30 random keyed
threats and 30 random empty positions against the board. If more than about
one in ten looks wrong to Justin or to the build session, fix the rule first.

## 7. Position pool

Per `specs/README.md` sources. Target sizes: S1–S3 share one pool of ~200
positions (each rung sees each position at most once per cycle); S4 ~200
own moves, half with a non-empty delta; S5 ~150 plus the sub-deck of ~50;
S6 ~120 windows. F windows he has already played go last in S6 order.

## 8. Out of scope

Best-move finding. Any eval. Own tactics beyond listing checks and captures
(H1 is null; README do-not-re-chase). Endgames. Counting drills as a
separate rung (L3 is 16% of hangs and no costlier; revisit only if S6
misses concentrate there).

## 9. Done when

`scanlib.py` passes its unit tests; the 60-position hand check in §6 is
done; all rungs render and store on a phone; export and backup round-trip;
cross-rebuild `cmp` passes against the P, R and F generators.
