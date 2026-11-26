# Trades from materially level positions (2026-11-25)

Exploratory, not pre-registered. Parked idea 3 from 2026-11-25 ("where does
he trade when level and shouldn't?"). Justin had believed taking every even
trade is right in any Caro, and also simplifies when short on clock.

Scripts: `chess/scripts/trades/` (`extract.py` → `deep.py` → `analyze.py`).
Outputs: `data/trades.csv.gz` (40,889 decision rows, |bal| ≤ 1),
`data/trades_d18.jsonl.gz` (1,624 depth-18 re-checks). Full tables:
`python3 analyze.py ../../data/trades.csv.gz ../../data/trades_d18.jsonl.gz`.

## Design

- **Decision point:** side to move not in check, material exactly level
  (P1 N3 B3 R5 Q9; the ±1 rows are used only for the clock section), at
  least one *even piece trade* available: capture of N/B/R/Q by the same
  value class (N, B one class), `hanging.see == 0`, opponent has a legal
  recapture on the square. took = the played move is one of those.
- **Scope:** Lichess 3+2 / 5+0, plateau blocks + F block (as egtruth), both
  sides. 30,177 level decision points in 5,098 games (me 15,306 / opp
  14,871; trades taken 4,062 / 4,439).
- **Error on the move (e05):** win-prob lost ≥ 0.05, depth 12, Lichess curve
  (~half a pawn near equality). Also checked at ≥ 0.10.
- **Benchmark:** the opponents in the same games. Rates standardized to his
  eval-band mix within each cell (bands −150 / −50 / +50 / +150), because he
  trades more often from some bands and the base error rate differs by band.
  Game bootstrap, 2,000 draws, seed 23. DiD = (me − opp on trades) − (me −
  opp on declines). DiD is **not meaningful in the opening**: opponents'
  declines there are bad because they are out of book against his prep.
- **Why not compare final scores of traded vs kept games:** whether a trade is
  offered, and taken, depends on the position, and conditioning on reaching
  an endgame biases scores (see "Conditioning" in method notes). The engine
  verdict on the trade move itself compares it with the alternatives in the
  same position, which sidesteps both.

## Results

1. **Even position → trading is a safe move, for both players.** After move
   12, level eval (−50..+50): his trades e05 13.9% vs his declines 39.5%;
   opponents 15.1% / 37.4%; me − opp on trades −1.3 [−5.0, +2.4]. At ≥ 0.10:
   4.9% vs 21.2%, opponents 4.9% / 21.9%. Slightly worse: 22.8% vs 45.8%.
2. **Clearly better (≥ +150 for him, material level) → his trades are no safer
   than his other moves**: 40.4% vs 43.2% (trade − decline −2.8 [−8.8,
   +3.4]); opponents in the same band 31.8% vs 46.6%. Me − opp on trades
   **+8.7 [+1.9, +15.6]**. Same in both eras (plateau 39.3% vs 32.9%; TREAT
   45.8% vs 26.4%). Mostly minor-piece trades (44.0% vs 35.3%; R and Q trades
   no gap). By family: London +15.7 [+5.2, +25.9]; Caro +4.3 [−7.2, +15.9].
   At ≥ 0.10 the direction holds, +4.3 [−2.2, +10.5], so most of the excess
   is half-pawn to one-pawn losses, not blunders.
3. **Depth-18 re-check** (Stockfish 16; Caro Advance + Caro Exchange all,
   London 300 per side): depth-12 rates reproduce (77% of depth-12 flags
   confirmed; depth 12 flagged 81% of depth-18 flags). Clearly better by the
   depth-18 eval: **41% vs 26%, +14.9 [+4.6, +25.0]**. Not clearly better:
   20% vs 16%, +4.3 [+0.1, +8.6].
4. **Caro.** Opening (moves 1–12): his trades are cheaper than opponents'
   (13.3% vs 16.0%) — Bxf3 in the Advance/Exchange setups is 12% (751
   trades). The belief "take the even trade in the Caro" is right in the
   opening and in even positions. After move 12: **Advance** 33.3% vs 21.8%
   (+11.5 [+2.0, +20.8]; depth 18: 31.7% vs 16.1%), consistent with result 2
   (median eval at these trades +0.78 for him, opponents +0.05). **Exchange**
   no gap (18.4% vs 24.7%), even though he takes trades far more often there
   (55% vs 32%). Pointer for the Caro study: …Bxf3 in the *other* Caro lines
   (mostly Two Knights / 3.Nc3 setups) costs on 33% of 80 tries, scattered
   over many positions, not one repeat.
5. **Take rate.** He trades less than opponents in the London opening (11% vs
   28%) and more than opponents after move 12 (44% vs 37%), most of all when
   slightly worse (49% vs 39%) and at even (49% vs 38%).
6. **Low clock (|bal| ≤ 1, after move 12).** ≤ 20 s: he takes 78% vs opp 56%.
   Trading does not detectably change his error rate over the next 10 own
   moves: +2.5 per 100 moves [−3.0, +8.0] (base 13.0), 103 games; 21–40 s
   −0.7 [−5.6, +4.2]. The trade move itself is not more error-prone than his
   alternatives (−9.7 [−32.8, +13.3]). Weighted regression on eval band, npm,
   balance, TC; game-clustered SEs. Thin: resolves ~±5 errors per 100 moves.

## What it changes

- **Rule of thumb:** level or worse → trade freely. Better with material level
  → a trade has to buy something concrete (material, their best defender,
  their active piece, a known-won ending); otherwise keep pieces and improve
  one. This is the textbook principle; his data say he doesn't apply it and
  his opponents (by this measure) do.
- **Simplifying when short of time:** no evidence against it.
- Feeds the parked Caro study: the Advance middlegame is where to teach "you
  are better, so keep the pieces"; the Exchange needs no trade advice.

## Decks (chess-study, group "When to trade")

- `tr_lessons` — five lesson cards (text in `scripts/trades_lesson_text.py`).
- `tr_keep` "Who's better? Trade or keep?" — reworked the same evening at
  Justin's request: **with level material the card must not reveal who is
  better**, because judging that is the skill. His own positions after move
  12, material level, an even trade available. Step 1: who is better (key from
  Stockfish 17.1 depth 18 winning chance: >= 62% you, 42–58% even, <= 38%
  them; gaps skipped). Step 2: trade or keep. Step 3: a good move (within 5
  points, of the right kind). Mix: 14 better/keep (he traded, best trade >= 8
  points below best), 8 better/trade, 8 even/trade, 6 worse/trade (trade
  within 3 of best, best non-trade >= 8 / 5 below). Built by
  `scripts/build_study_trades.py`; own cache `study/engine_cache_trades.json`.
- **Standing rule for future decks:** any exercise on a materially level
  position withholds the evaluation until after the answer.

## Limits

- e05 at depth 12 is a low bar and noisy one ply at a time; every headline
  figure is a rate over hundreds of trades and survives depth 18.
- "Better" is the engine's view; whether he *felt* better is unknown.
- Even trades only. Trades offered by putting a piece where it can be taken
  (allowing a trade), pawn trades and uneven trades (exchange sacs, BxN
  against a defended pawn) are not covered.
