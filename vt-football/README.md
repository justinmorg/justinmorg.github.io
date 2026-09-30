# Virginia Tech football play-by-play

Games, drives, and plays for Virginia Tech football: 1987-2000 from VT's official stat-crew
files (hokiesports.com), 2001 on from the [CollegeFootballData API](https://collegefootballdata.com),
with the stat-crew files also covering most of 2001-2019.

**For analysis, query `data/unified/`** (see "Unified play table" below). It picks the best source
for each game and repairs known CFBD coding problems; the raw per-source tables stay as pulled.

## Layout
- `data/games/<season>.parquet`: schedule, scores, line scores, venue, Elo
- `data/drives/<season>.parquet`: every drive for both teams (clock fields in seconds)
- `data/plays/<season>.parquet`: every play: down, distance, yard line, play type,
  play text, PPA/EPA (`ppa`, available in later seasons), game clock in seconds
- `fetch.py`: refresh script
- `data/unified/games.parquet`, `data/unified/plays/<season>.parquet`: one row per game and one
  row per scrimmage play across all sources (built by `normalize.py`)
- `data/unified/validation.csv`: per-game check against official box scores (`validate_box.py`)

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

## Unified play table
`python normalize.py` rebuilds `data/unified/`; `python validate_box.py` checks it. Run both after
any refresh or new crawl.

- **Source per game:** hokiesports XML if the game has one, else the StatCrew text report, else
  CFBD. `games.source` records the choice; every play row has `source`, `cfbdGameId`, `hsGameId`.
  This also removes the 2003-at-Virginia double count (CFBD partial + hokiesports full).
- **Plays:** scrimmage plays only (downs 1-4), `category` = rush / sack / comp / inc / int,
  `yards` NCAA-style (sacks negative, incompletions and interceptions 0), `fumble` flag,
  `vtOffense` flag, `opponent`. Goal-to-go `distance` is set to yards to goal.
- **Validation:** team plays and yards per game vs. the `<totals>` block of each XML. Unified
  totals are within 1.1% of the official box scores in every season 1987-2019 (most under 0.7%).
- Coverage by source (games with play-by-play / games played):

  | Seasons | Source |
  |---|---|
  | 1987-2000 | hokiesports (gaps: 1997 Gator Bowl, 6 of 12 games in 1998, 2000 Gator Bowl) |
  | 2001-2004 | hokiesports, except 2001 Gator Bowl and 2003 Insight Bowl (CFBD), 2004 Sugar Bowl (StatCrew text); 2002 West Virginia has none |
  | 2005-2007 | CFBD (repaired), except 2 games in 2005 and 1 in 2006 |
  | 2008-2019 | hokiesports for 10-14 games a season; the rest CFBD (repaired) |
  | 2020 on | CFBD (repaired) |

## CFBD data quality
Found by comparing CFBD play-by-play with the official box totals (Sept 2026). `normalize.py`
repairs what the play text allows.

| Problem | Seasons | Handling |
|---|---|---|
| Sacks recorded as 0 yards; the loss is only in the text | 2006-2012; 26 of 50 in 2021 | yards parsed from text |
| Every pass typed plain `Pass`; interceptions carry return yards as offense yards; sacks 0 yards | 2005 | classified and repaired from text |
| Sacks missing entirely (~71 plays) | 2013 | hokiesports used for all 13 games |
| Fumble plays carry the return yardage in `yardsGained` | 2014 on | scrimmage yards parsed from text |
| Different, coarser play-by-play feed; many plays off by a few yards | 2001 | hokiesports used for 11 of 12 games |
| Occasional play credited to the wrong team | e.g. 2014 Boston College, Georgia Tech | not repaired |

After repair, CFBD is within about 1-2% of the box scores for 2004, 2008-2012 and 2015-2019;
2014 is about 3%. Don't use raw `data/plays/` yardage for 2005-2016 without these fixes.

## Refresh
```bash
export CFBD_API_KEY=...   # never commit the key
python fetch.py 2026      # the current season is always re-pulled
```
Past seasons already on disk are skipped unless `--force` is given.

## Query
```python
import duckdb
duckdb.sql("select * from read_parquet('data/unified/plays/*.parquet') limit 5")   # analysis
duckdb.sql("select * from read_parquet('data/plays/*.parquet') limit 5")           # raw CFBD
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
  Known holes: 1997 Gator Bowl, 1998 (6 of 12 games), 2000 Gator Bowl, 2002 West Virginia. Only
  2 games exist for 2005, 1 for 2006, none for 2007. Crawled through 2019; games per season with
  XML, 2001-2019: 11, 13, 12, 12, 2, 1, 0, 11, 12, 14, 13, 12, 13, 13, 12, 14, 13, 10, 13.
- Source errors handled in `parse_tas.py`: `DATE_OVERRIDES` fixes ID 5285 (2001 at Rutgers, dated
  2002-09-22 in the XML, so it used to be filed under 2002). The 2013 Sun Bowl (5455) keys each
  touchdown and its PAT as one `X` record; `normalize.py` keeps the scrimmage part of those.

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

## 1987-1998 (hokiesports.com only)
131 games in `data/hokiesports/` (IDs 5120-5257), every game with a box score link on the
schedule pages. Each game's line score sums to its final, every game has four quarters of plays
(plus the 1998 overtime at Miami, 27-20), and season records match VT's official ones through 1996.
Missing: the 1997 Gator Bowl vs. North Carolina (VT 7-4 here, 7-5 officially) and 6 of 12 games in
1998 (the 6 present are all wins; the 9-3 season's three losses have no box score).

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
