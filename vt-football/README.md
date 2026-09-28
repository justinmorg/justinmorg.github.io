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
