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
  West Virginia (Nov. 20), which has no XML on the official site either.
- 2003 Boston College (week 14) and the 2004 Sugar Bowl vs. Auburn: no plays

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
