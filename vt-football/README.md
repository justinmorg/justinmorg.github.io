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
- 2002: no play-by-play for any regular-season game (drives are also mostly missing)
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
