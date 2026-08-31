# pending/

Blocks that exist in the repo but are **not part of the analysed corpus**.
Nothing here is counted in any figure in `chess/README.md`.

Deliberately in a subdirectory: the analysis scripts glob `chess/data/*.pgn.gz`,
so a block dropped straight into `data/` would be silently swept into corpus
totals. Moving a file out of `pending/` is the act that admits it.

## jamorgan_2026aug_freshbatch_annotated.pgn.gz

220 rated Lichess blitz games, 2026-08-19 → 2026-08-31, all 300+0. Pulled as a
raw Lichess export and re-annotated locally at depth 12 with `annot_inc.py`;
the server evals that came with the export (22% ply coverage, unknown depth)
were discarded. Eval coverage is 16,073 / 16,073 plies.

The boundary game `LjN5QcUZ` — already in `jamorgan_blitz_2026_analyzed.pgn.gz`
— was dropped before annotation, so this block is 220 net new games with no
overlap.

**Not merged into the 2026 corpus, on purpose.** At 220 games it is below the
~450-game floor at which a block can distinguish anything, and neither rating
trigger has fired (point-in-time high 1513 against the 1520 override; three days
outside the 1310–1455 band against the three weeks required; trailing-200 mean
1429, still inside the band and 20 points under the Feb–Mar 2026 excursion that
was tested and closed as a random walk).

It is committed only so that `chess-drills/fresh/` is reproducible:

    python3 chess/scripts/hanging.py <this block, gunzipped> light
    python3 chess/scripts/build_drills2.py hits_light.json chess-drills/fresh/index.html

Hits: 48 raw (34 missed their threat / 14 hung it myself), 34 after the 0.02
win%-error floor (22/12).
