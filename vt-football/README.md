# Virginia Tech football play-by-play

Games, drives, and plays for Virginia Tech football: 1987-2000 from VT's official stat-crew
files (hokiesports.com), 2001 on from the [CollegeFootballData API](https://collegefootballdata.com),
with the stat-crew files also covering most of 2001-2019 and all games from 2024 on.

**CFBD is frozen.** No new VT play-by-play is pulled from CFBD; the CFBD games already in the repo
stay until they are replaced, over time, with better sources (official stat-crew XML / WMT JSON,
StatCrew text reports). New games come from hokiesports.com via `parse_wmt.py` (see "Refresh").

**For analysis, query `data/unified/`** (see "Unified play table" below). It picks the best source
for each game and repairs known CFBD coding problems; the raw per-source tables stay as pulled.

## Layout
- `parse_wmt.py <boxId>`: late-2020-on official stat-crew data from the WMT stats API behind
  hokiesports.com box scores (raw JSON in `hokiesports/raw_wmt/`), written to `data/hokiesports/`
  in the same shape as the XML games, so `normalize.py` and `validate_box.py` treat them as
  hokiesports. This is the source for the current season; 2026 Pitt (box 22963) matches the official
  team totals exactly. All of 2020-2023 (box IDs 5535-5583; loaded Oct 25, 2026), 2024 (5585-5596,
  bowl 21742) and 2025 (21761-21772) are loaded from WMT. Many 2020-2022 box score pages embed the
  wrong WMT game (5535, NC State 2020, linked UNC 2020; 5537 linked a 2019 game), so
  `hokiesports/wmt_ids.json` maps box IDs to WMT ids from WMT's own VT team-season schedules
  (`api.wmt.games/api/statistics/games?team_id=<VT team id>`), and `parse_wmt.py` stops if a box
  page's date doesn't match the WMT game's. 2021 at Georgia Tech (5553) has no plays in WMT and
  is skipped. Bad-snap team fumbles written "TEAM rush for loss of N yards ... fumble" (no clock
  prefix) are typed as team rushes. 2020-2023 unified totals are within 0.3% of the official box
  (CFBD was off 2.4-6.1%).
  unified team totals are within 0.5% of the official box. The biggest gap, 2024 Duke VT rushing
  (176 vs 190), is in the box itself: VT's individual rushing lines sum to 176.
  Repairs: WMT sometimes stores 0 yards (or the recoverer as rusher) on a fumbled rush, so the text
  yardage is used and the rush goes to TEAM; intentional grounding is a QB rush for the loss, as in
  StatCrew; spot fouls like "8 yards gain (1)" and lateral plays keep the action yardage.
  WMT leaves some snaps out of its `plays` list and keeps them only in the flat `actions` list:
  kneel-downs, dead-ball penalties (false start, delay of game, offside ... NO PLAY) and some onside
  kicks. `parse_wmt.py` merges them back in action-id order (fixed Oct 25, 2026; 109 plays across
  2024-2026 were missing before). After the fix, 2024-2026 unified scrimmage plays match the box in
  every team-game but one (2025 California defense, 1 play short).
- `data/games/<season>.parquet`: schedule, scores, line scores, venue, Elo
- `data/drives/<season>.parquet`: every drive for both teams (clock fields in seconds)
- `data/plays/<season>.parquet`: every play: down, distance, yard line, play type,
  play text, PPA/EPA (`ppa`, available in later seasons), game clock in seconds
- `fetch.py`: CFBD pull script (retired for VT play-by-play; kept for reference and for the CFBD data already on disk)
- `data/unified/games.parquet`, `data/unified/plays/<season>.parquet`: one row per game and one
  row per scrimmage play across all sources (built by `normalize.py`)
- `espn_pbp.py <eventId>`: interim play-by-play from ESPN's public game summary for a game whose
  official stat-crew data isn't posted yet (raw JSON in `data/espn/pbp/raw/`, tables in
  `data/espn/pbp/{games,plays}/`, stat-crew column shape). `normalize.py` ranks it below hokiesports
  and StatCrew text and above CFBD, so loading the WMT game later replaces it automatically.
  Used for 2026 at Clemson (ESPN 401858276) until WMT box 22966 posted plays later on Oct. 25; the
  ESPN data stays on disk but the game now comes from WMT. Penalty parsing (`penalties.py`) skips ESPN-sourced games for now.
- `data/unified/validation.csv`: per-game check against official box scores (`validate_box.py`)

## Defense rankings by season (`defense_rank.py`)
`python howell.py` pulls every I-A/FBS score since 1987 from James Howell's historical scores
(jhowell.net, one page per team; raw pages gitignored) into `data/howell/games.csv`.
`python defense_rank.py` fits opponent-adjusted scoring ratings per season (ridge least squares:
league mean + offense + defense + home; non-I-A opponents pooled) and joins VT's play-level
defense from `data/unified/` and the drive-model rating (2016 on) into
`data/derived/vt_defense_by_season.csv`. The current season comes from `data/espn/games/`
(2002-2009 added Oct 25, 2026 via `espn.py`). Points-based, so return/defensive TDs and short
fields off VT turnovers count against the defense; the drive model corrects for those from 2016.
As of Oct 2026 the top seasons by adjusted rank are 2004 (2nd), 2005 and 1998 (3rd),
1999/2001/2007 (4th), 2017 (5th), 2006 and 1995 (6th); the worst are 2018 (92nd) and 2025 (83rd).

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
- **Hokiesports audit (Oct 25, 2026):** every box score linked from a hokiesports.com schedule
  page, 1987-2026, is loaded (2021 at Georgia Tech, 5553, has no plays in WMT). The unlinked IDs
  between 5120 and 5596 are all VT games too (1998's six missing games, the 1997/2000/2001/2003
  bowls, 2002 West Virginia, 2005-2007, and the CFBD games in 2008-2021; 5570 is the cancelled
  2022 Virginia game), but their pages are empty shells: statistics.hokiesports.com returns 404
  for them, so no hokiesports play-by-play exists for any game not already in the repo.
  stats.hokiesports.com has box pages for 2005-2007 (e.g. 2006 = ids 6031-6042, 8399) with
  team stats and scoring drives but no play-by-play.
- **ESPN check for non-stat-crew games:** `python espn_box_totals.py` saves ESPN's team box for
  games without an official box (`data/espn/box_totals.csv`); `validate_box.py` then prints a
  third table, "unified vs ESPN box". ESPN's box equals the official stat-crew totals where both
  exist. ESPN play-by-play for these games was tested as a replacement for repaired CFBD and was
  worse (5.8% vs 2.3% of yards off the box), so CFBD stays. Neither source has 2002 West Virginia.
- **Validation:** team plays and yards per game vs. the `<totals>` block of each XML. Unified
  totals are within 1.1% of the official box scores in every season 1987-2019 (most under 0.7%).
- Coverage by source (games with play-by-play / games played):

  | Seasons | Source |
  |---|---|
  | 1987-2000 | hokiesports (gaps: 1997 Gator Bowl, 6 of 12 games in 1998, 2000 Gator Bowl) |
  | 2001-2004 | hokiesports, except 2001 Gator Bowl and 2003 Insight Bowl (CFBD), 2004 Sugar Bowl (StatCrew text); 2002 West Virginia has none |
  | 2005-2007 | CFBD (repaired), except 2 games in 2005 and 1 in 2006 |
  | 2008-2019 | hokiesports for 10-14 games a season; the rest CFBD (repaired) |
  | 2020-2023 | hokiesports (WMT JSON, box IDs 5535-5569 and 5571-5583): all 48 games except 2021 at Georgia Tech (WMT has no plays; CFBD) |
| 2024 | hokiesports (WMT JSON, `parse_wmt.py`, box IDs 5585-5596 and 21742 for the Duke's Mayo Bowl): all 13 games |
| 2025 | hokiesports (WMT JSON, `parse_wmt.py`, box IDs 21761-21772): all 12 games |
| 2026 on | hokiesports (WMT JSON, `parse_wmt.py`): 2026 box IDs 22958-22960, 22962-22966 (VMI through Clemson) |

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

## Drive model, defense vs. expectation, weather
`drive_model/` (Oct 2026): expected points per drive from starting field position, opponent-adjusted
offense/defense ratings, VT's defense scored against expectation game by game, projections for
remaining opponents, and game-time weather from airport observations. All FBS games from ESPN
play-by-play. See `drive_model/README.md` for the pipeline and findings.

## ESPN results and rebuilt Elo (no CFBD quota needed)
- `espn.py 2014-2026 [--odds]`: every FBS game's result from ESPN's public API (no key, no quota)
  into `data/espn/games/<season>.parquet` (2010 on); `--odds` adds ESPN's stored betting line
  (`homeSpread` = home team's line) into `data/espn/odds/` (2016 on, ~100% of FBS-vs-FBS games).
- `elo.py`: FiveThirtyEight-style Elo for all teams from those results (margin-of-victory
  multiplier, 55-point home field, ratings regressed 20% toward the mean each offseason; K=35;
  tuned on 2014-2025 log loss with `--tune`). Writes `data/elo/games.parquet` (pregame ratings,
  home win probability, Elo spread for every game) and `data/elo/ratings_current.csv`.
  18 Elo points is about 1 point of spread. Re-run `espn.py <season>` then `elo.py` weekly.
- `elo_backtest.py` (output in `data/elo/backtest.txt`): on 7,528 FBS-vs-FBS games 2016-2025,
  the Elo favorite won 70.4% vs 73.0% for the betting favorite; Brier 0.189 vs 0.175; spread
  error 13.3 vs 12.3 points. Elo adds nothing once the line is known, and betting Elo against the
  line hits 48.6%. Use it when no line exists (future weeks), not to beat one.
- CFBD's own `homePregameElo`/`awayPregameElo` in `data/games/` are frozen at the date of the
  last CFBD pull; for future games prefer `data/elo/`.
- `espn_league_pbp.py <season(s)> [--team NAME] [--force]`: scrimmage play-by-play for other teams
  from ESPN game summaries (parsed with `espn_pbp.parse`; no raw JSON kept). Without `--team`:
  every completed game with an FBS team, `data/espn/league_pbp/<season>.parquet` (2026 on disk,
  ~3 MB a season). With `--team`: `data/espn/team_pbp/<team-slug>/<season>.parquet` (Penn State
  2014-2025 on disk, for comparing Franklin/Pry/Howle-era tendencies). Columns include offense,
  defense, offFBS/defFBS, ESPN drive order, category, yards, success, explosive. Use these for
  national ranks and other programs; compare a team with itself, since ESPN yardage is a bit
  looser than the stat-crew tables. Re-run `espn.py <season>` first for new weeks.

## Refresh
New games come from the official stat-crew data behind each hokiesports.com box score; do not
pull VT play-by-play from CFBD.
```bash
python parse_wmt.py <boxId>   # hokiesports.com/boxscore/<boxId>; one or more ids
python normalize.py           # rebuild data/unified/
python validate_box.py        # check against the official box
```
Replacing a CFBD game: load its stat-crew source (WMT, XML or StatCrew text); `normalize.py`
prefers stat-crew sources over CFBD, so the CFBD rows drop out of `data/unified/` automatically.

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

## Derived: penalty profile (pre-snap / football / discipline)
`python penalties.py [--espn]` classifies every penalty by type into three buckets and writes
`data/derived/penalties_by_play.csv` (one row per penalty, incl. declined/offsetting) and
`data/derived/penalties_by_game.csv` (VT and opponent accepted count and yards per bucket, plus
official totals). `--espn` re-pulls ESPN team penalty totals for CFBD games
(`data/espn/penalties/vt_games.parquet`).
- **pre_snap:** false start, illegal formation/procedure/shift/motion, illegal substitution, too many
  men, delay of game, offside, encroachment, neutral zone.
- **football:** holding, pass interference, illegal block/clipping/chop, illegal use of hands,
  illegal contact, tripping, ineligible downfield, face mask, intentional grounding, running into
  the kicker, kick-catch interference.
- **discipline:** unsportsmanlike, taunting, unnecessary roughness, generic "personal foul",
  roughing the passer/kicker, late hit, horse collar, targeting.
- By type only; edge cases not hand-checked. Older StatCrew games often say just "personal foul".
- Accuracy vs official counts: hokiesports games exact in ~93% (within 1 in ~98%); all 18 WMT games
  (2025, 2026) exact in count and yards for both teams. WMT quirks handled: replay "(Original Play: ...)"
  text is ignored, glued codes ("PENALTY VTFalse Start") are split, two fouls in one PENALTY string are
  both counted, and dead-ball penalties missing from the play table are read from the raw JSON. CFBD games (2020-2025 especially) undercount: exact in ~65%,
  within 1 in ~90%, because CFBD's play-by-play drops some penalty snaps. 2005 has no ESPN totals.
  Penalty yards are missing from some newer CFBD text (`*_ydsMissing`).

## Derived: VT takeaways
`python takeaways.py` writes `data/derived/vt_takeaways_by_game.csv` and
`data/derived/vt_takeaways_by_season.csv`: opponent interceptions thrown plus fumbles lost, per
game. Official box totals where available (355 games, includes special-teams fumbles), else
ESPN game boxes from 2010 on (`espn_box.py`), else play text with hand-checked recoveries; see
the script's docstring. CFBD play text misses or double-counts some turnovers in 2021-2025.

## Derived: FBS takeaways
- `espn_box.py 2010-2026 [--force]`: interceptions thrown, fumbles lost and turnovers for both
  teams in every game in `data/espn/games/` (one ESPN summary call per game, no quota) into
  `data/espn/box/<season>.parquet`. Run `espn.py <season>` first to pick up new games.
- `fbs_takeaways.py`: FBS average, median and 10th/90th percentile takeaways per game by season,
  with VT's value and rank, into `data/derived/fbs_takeaways_by_season.csv` (team-season rows in
  `fbs_team_takeaways_by_season.csv`). ESPN dates are UTC, so night games show the next day.

## Derived: game-phase splits (first half / first two 2H drives / rest)
`phase_splits.py` writes counts (plays, successes, yards, runs, sacks, explosives, 1st-down plays
and 1st-down runs) by game, side and phase, so any set of games re-aggregates exactly:
- `data/derived/phase_splits_by_game.csv`: VT, every season in `data/unified/`, `oppFBS` flag
  from ESPN results (2010 on). `python phase_splits.py`.
- `data/derived/phase_splits_league_<season>.csv`: every team in `data/espn/league_pbp/`.
  `python phase_splits.py --league 2026`.

Phases: `1H`; `2H_d1-2` = the offense's first two drives that start in Q3 or later; `2H_d3+`.
Success: 50% of distance on 1st down, 70% on 2nd, all of it on 3rd/4th, never on an interception.

Built for the October 2026 finding that VT's offense stalls right after halftime. Through 7 FBS
games (Clemson), VT's first two second-half drives ran 30% success / 3.5 yds per play vs 44% /
5.9 the rest of the game. The definition (first two drives) was fixed before the Clemson game,
which fit the pattern (two three-and-outs). Nationally the same gap looks like noise (team-to-team
spread about equal to sampling error), so keep tracking it before calling it real.
Re-run after each game: `parse_wmt.py`, `normalize.py`, `phase_splits.py`.
