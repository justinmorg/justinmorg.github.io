# Long-think classification and clock lens (2026-11-25, exploratory)

Run in order. Paths are the sandbox layout used on 2026-11-25
(`/home/claude/features7` = features.py output for the six settled blocks
plus `TREAT`; `/home/claude/blocks/` = unzipped block PGNs; Stockfish at
`/home/claude/sf/x/usr/games/stockfish`). Edit the constants at the top to
re-run elsewhere.

1. `extract.py`: 3+2 own moves from the 2026 and F blocks. Long = spend
   ≥ 15s (n = 3,574); quick = spend ≤ 5s, move 8+, random 1,500 (seed 23).
   Writes the FEN before each move.
2. `mpv.py SHARD NSHARDS BUDGET_S`: Stockfish depth 12, multipv 8, plus the
   played move if it is not in the top 8. Resumable.
3. `classify.py`: Lichess win-probability scale. A move is good if it is
   within 5 points of the best. Categories in priority order: already lost
   (best < 20%), winning (best > 85%, 2+ good moves), only move (1 good,
   runner-up ≥ 10 points worse), 2–3 good, 4+ fine. Output:
   `chess/data/longthinks_classified_2026.csv.gz`.
4. `lens.py`: splits each F-block move's change in expected score
   (`clockmodel.py`) into a clock part (board held fixed) and a board part.

Multipv 8 caps the "fine" count at 8. Depth 12 multipv is noisier than the
single-line labels. The 5-point threshold is a choice, not a calibration.
