# Virginia Tech football play-by-play

Games, drives, and plays for every Virginia Tech game from 2001 on, pulled from the
[CollegeFootballData API](https://collegefootballdata.com). Play-by-play coverage
starts in 2001.

## Layout
- `data/games/<season>.parquet`: schedule, scores, line scores, venue, Elo
- `data/drives/<season>.parquet`: every drive for both teams (clock fields in seconds)
- `data/plays/<season>.parquet`: every play: down, distance, yard line, play type,
  play text, PPA/EPA (`ppa`, available in later seasons), game clock in seconds
- `fetch.py`: refresh script

## Known gaps in the CFBD source
- 2002: no play-by-play for any regular-season game (drives are also mostly missing).
  Filled from hokiesports.com (`data/hokiesports/`, IDs 5295-5308) for all 13 games except
  West Virginia (Nov. 20), which has no play-by-play anywhere found so far. A partial record
  (scoring summary, team stats, game details) is in `data/stats_hokiesports/` (box 5988).
- 2003 Boston College: no plays; 2003 at Virginia: plays stop after the 3rd quarter. Both are
  filled from hokiesports.com (IDs 5319, 5320).
- 2004 Sugar Bowl vs. Auburn (Jan. 3, 2005): no plays in CFBD and no box score on hokiesports.com.
  Filled from Auburn's StatCrew text report (`data/statcrew_text/`, game id `20050103-AU`).
- CFBD's `offenseScore`/`defenseScore` don't always match the final score (some look pre-play,
  a few are just wrong), so don't use them to check completeness.

## Refresh
```bash
export CFBD_API_KEY=...   # never commit the key
python fetch.py 2026      # the current season is always re-pulled
```
Past seasons already on disk are skipped unless `--force` is given.

## Query
```python
import duckdb
duckdb.sql("select * from read_parquet('data/plays/*.parquet') limit 5")
```

## Second source: hokiesports.com (TAS/StatCrew XML)
VT's official stats site (statistics.hokiesports.com, box score IDs like 5295) serves the
original stat-crew game files: every play includes tacklers, penalties, fumble recoveries,
and drive summaries. Used to fill CFBD gaps (2002) and possibly pre-2001 seasons.
- `parse_tas.py <file.xml> --source-id <hokiesports id>` writes
  `data/hokiesports/{games,drives,plays,players}/<id>.parquet` and keeps the raw XML in
  `hokiesports/raw/`.
- The play `clock` is the last clock the scorer logged (drive start, scores, timeouts),
  not an exact per-play time.
- Every game's plays table has the same columns (`PLAY_COLS` in `parse_tas.py`), even when a
  game has no field goals, interceptions, etc.
- On a touchdown, `nextPossession` is the scoring team; use it to credit return and defensive
  TDs. A blocked PAT returned for 2 is typed `X` with "defensive PAT" in the text.
- Special-teams scores are credited to the kicking team's `offense` in TAS (e.g. a VT punt
  return TD shows `offense` = the punting team); use the play text or `nextPossession`.

### Where the XML lives
- `statistics.hokiesports.com/stats/game/<id>` is a JS app; it loads the raw file from
  `https://statistics.hokiesports.com/api/v1/game/xml/<id>` (plain `<fbgame>` XML, no auth).
- Box score IDs come from `https://hokiesports.com/sports/football/schedule/season/<year>`
  (`href="/boxscore/<id>"`). IDs start at 5120 (1987) and are mostly sequential; unlinked
  IDs in the range all 404.
- Coverage: full play-by-play from 1987 through part of 2020 (retro-keyed in 2009-2011 for
  older seasons). Late 2020 on, box scores move to wmt.games and this endpoint 404s.
  Known holes: 1998 (6 of 12 games), 2002 West Virginia, 2005 (2 games), 2006 (1), 2007 (none).

### Crawl
```bash
python crawl_hokiesports.py 1987 2002 --dry-run   # list IDs
python crawl_hokiesports.py 1987 2020             # 34 schedule pages + ~366 games, ~14 min at 2s
```
Skips games already in `hokiesports/raw/` + `data/hokiesports/games/`; status per ID in
`hokiesports/manifest.csv`. Needs `pyarrow`.

## Third source: StatCrew text reports
For games with no `<fbgame>` XML anywhere, the plain-text StatCrew report (box score, drive
chart, play-by-play) can still be parsed.
- `parse_statcrew_text.py <report.txt> --game-id ... --cfbd-id ... --season ... --date ...
  --visitor ... --vcode ... --vletter ... --home ... --hcode ... --hletter ...` writes
  `data/statcrew_text/{games,drives,plays}/<game-id>.parquet` with the same play columns as the
  XML games (`PLAY_COLS`), plus `shotgun`, `patType`, `passDefender`.
- Raw reports live in `statcrew_text/raw/`.
- No players table (the text report's stat tables aren't parsed).
- 2005 Sugar Bowl (`20050103-AU`, CFBD 250030259): all team totals, individual rushing and
  receiving lines, drive play counts, and the score by quarter match the report's own box score.

## 1999-2000 (hokiesports.com only; CFBD starts in 2001)
All 23 games with a box score link are in `data/hokiesports/` (1999 IDs 5258-5269, including
the Sugar Bowl vs. Florida State; 2000 IDs 5271-5281). Every game's scoring plays reconcile with
its line score, and line scores and attendance match stats.hokiesports.com for the 21 games
it has (it has no stats for 1999 Clemson or 2000 Miami). The 2000 Gator Bowl vs. Clemson has no
play-by-play; a partial record is in `data/stats_hokiesports/` (box 5965).

## Fourth source: stats.hokiesports.com box scores (partial records)
`https://stats.hokiesports.com/football/box/?<id>=` pages have a line score, game details,
scoring summary and team stats, but no play-by-play. IDs are mostly sequential by game (1998 bowl
5940, 1999 5941-5952, 2000 5954-5965, 2001 from 5966, 2002 5977-5991; 5943 and 5953 are empty
and 5962 holds a 2005 game).
- `parse_stats_hokiesports.py <id> [--cfbd-id ...]` saves the page to `stats_hokiesports/raw/`
  and writes `data/stats_hokiesports/{games,scoring,teamstats}/<id>.parquet`.
- Used for 2002 West Virginia (5988, CFBD 223240259; matches CFBD's line score and attendance)
  and the 2000 Gator Bowl vs. Clemson (5965).
- The site's derived averages are sometimes wrong (VT "Average Per Rush 0.0"); stored as published.
