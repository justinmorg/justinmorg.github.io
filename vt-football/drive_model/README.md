# Drive model: expected points, defense vs. expectation, weather (2016-2026)

Built Oct 25, 2026 to judge VT's defense against expectation and project the rest of the
season; extended the same day to 2016-2026 to measure weather. Every script runs from this
folder (each one `chdir`s here). Sources are ESPN's public game summaries (no key) and Iowa
Environmental Mesonet airport observations (no key); no CFBD.

## Multi-season weather pipeline (current)

| Step | Script | Output (committed) |
|---|---|---|
| Drive table + venue/kickoff per season; summaries parsed in memory, never saved | `season_drives.py 2016 ... 2026` | `drives/<season>.parquet`, `drives/games_<season>.csv` |
| Venues geocoded (retries, second pass), domes and retractable roofs flagged | `venues.py` | `venues.csv`, `game_venues.csv` |
| Up to 3 candidate airport stations per venue; hourly obs per station-season | `wx.py [seasons]` | `venues.csv` (+ `asos/`, gitignored, ~250 MB) |
| Weather from 30 min before kickoff to +3.5 h | `gamewx.py` | `game_weather.csv` |
| Per-season curve + ratings; pooled weather fit with bootstrap | `wxpool.py` | `ep_curves.csv`, `team_ratings.csv`, `game_resid.csv`, `wx_effects.csv`, `wx_bands.csv` |
| VT 2026 defense re-scored with the pooled weather terms | `vtwx.py` | `vt_def_wx.csv` |

Shared code (drive parser, cleanup, curve, ratings) is in `dm.py`. Refresh after a week:
`python ../espn.py 2026 --force`, then `season_drives.py 2026 --force`, `venues.py`,
`wx.py 2026`, `gamewx.py`, `wxpool.py`, `vtwx.py`. Seasons covered: everything ESPN lists as
completed, including conference title games, bowls and the CFP. ESPN has no drive data for
17/5/3/1/5 games in 2016-20 and 48/39/8/18/2 in 2021-25 (mostly FCS opponents). Weather stations
must have reported since before 2016. 2020 (COVID) is included with its own season intercept;
dropping it doesn't move the estimates.

**Drive points fix.** Per-play scores inside ESPN drives carry stale values on some plays
(trailing "End of Half" markers especially), which zeroed about 9% of 2021-25 touchdown drives
and some 2026 ones. Points now come from ESPN's scoring-play list, matched to drive plays by id
and credited to the drive's offense (a drive keeps 3 or 6-8; defensive/return scores and
safeties drop out). Team drive points now equal the final score in 76-80% of team-games every
season (the rest are return/defensive scores and safeties) versus 54-72% with the old rule. VT's 2026
opponents' totals are unchanged. 2026 is re-cut with the same rule, so its numbers here differ
slightly from the 2026-only tables below.

**Method.** Per season: isotonic expected-points curve on start position (FBS vs FBS, late
drives out) and ridge team ratings (offense + defense + home, lambda 40). Pooled: each FBS-vs-FBS
game's mean residual per drive is regressed (weighted by drives, season intercepts) on weather.
Wind bands are outdoor games only; domes/retractable roofs get their own indoor term. Rain =
share of observations with rain/drizzle/snow/storms (1 = wet throughout). Cold = below 40 F.
Errors: 2,000 bootstrap draws over games. A joint fit (ratings refit on weather-adjusted points
until stable) gives estimates about 20% larger, i.e. the two-stage numbers are slightly
conservative because ratings absorb some of a windy home park's weather.

## Findings, 2016-2026 (7,843 FBS-vs-FBS games, 181,276 drives)

| Term (pts/drive) | Estimate | Boot SE | 95% range | Games |
|---|---|---|---|---|
| Wind 10-15 mph (vs 0-10) | -0.03 | 0.02 | -0.07 to 0.00 | 1,379 |
| Wind 15-20 | -0.09 | 0.03 | -0.16 to -0.03 | 370 |
| Wind 20-25 | -0.17 | 0.07 | -0.31 to -0.03 | 75 |
| Wind 25+ | -0.30 | 0.13 | -0.55 to -0.02 | 20 |
| Wind, linear above 8 mph (per mph) | -0.011 | 0.002 | -0.015 to -0.006 | |
| Wind, linear above 15 mph (per mph) | -0.024 | 0.006 | -0.037 to -0.012 | |
| Rain throughout | -0.26 | 0.04 | -0.33 to -0.18 | 439 with rain half the time+ |
| Cold below 40 F | -0.03 | 0.03 | -0.08 to +0.03 | 495 |
| Indoor (vs outdoor calm) | -0.04 | 0.03 | -0.10 to +0.02 | 359 |

0-10 mph: 5,640 games. Raw points per drive by band: 0-10 2.21, 10-15 2.16, 15-20 2.08,
20-25 2.04, 25+ 1.89, indoor 2.19.

- Wind is a steady drag that starts low: about 0.011 points per drive per mph above 8 mph
  (5 SE). A 20 mph game costs ~0.13 per drive, ~3 points per game for both teams combined; a
  30 mph game ~0.24 per drive. The bands rise in step (-0.03, -0.09, -0.17, -0.30).
- Threshold: the fit is best at 8-10 mph and gets clearly worse above 12; bootstrap picks 8 or
  10 mph 79% of the time. There is no cliff at 20 mph.
- Stable across periods: the linear slope is -0.012 for 2016-20 and -0.009 for 2021-26;
  dropping 2020 (COVID) changes nothing. Individual bands bounce around within each half.
- The 2021-26 fit's 25+ estimate (-0.53 on 6 games) was too big; with 20 games it is -0.30.
- Rain is the strongest weather effect (-0.26 for rain throughout, about 6 SE).
- Cold under 40 F has no measurable effect once wind and rain are accounted for.
- Data quality for 2016-20 matches recent seasons (drive points equal the final in 76-80% of
  team-games; 1-17 games a season without drive data; ~50 of 9,100 games without weather, 14 of
  them with no venue in ESPN). A joint fit gives effects about 15-20% larger than the two-stage
  numbers above.

## VT 2026 defense with the pooled weather terms (`vtwx.py`, VT games left out of the fit)

Boston College (Sept 26; 30 mph, gusts 45, rain throughout): VT allowed 14 on 12 drives against
26.7 expected in calm weather, so -12.7 unadjusted. Weather is worth -5.8 points (linear wind,
SE 0.8) to -6.5 (wind bands, SE 1.7), leaving VT 6.5-7.2 points better than expected: about half
the raw margin. Season to date (93 drives): -13.8 points vs expectation unadjusted, -8.1 to -8.5
weather-adjusted; without BC VT's defense is average (-0.02 per drive). Season defensive
rating: -0.10 pts/drive (54th of 138 FBS) unadjusted, -0.06 (55th-56th) weather-adjusted.

---

# 2026-only model (original)

Raw downloads are gitignored and re-created by the scripts: `espn_pbp/raw/` (ESPN summaries,
~280 MB for one season) and `asos/` (hourly airport observations, ~8 MB). `venues.py`, `wx.py`
and `gamewx.py` have since been generalized (above); `game_weather.csv` now covers all seasons
and `wxfit.py` still runs on it.

## Pipeline (run in this order)

| Step | Script | Output |
|---|---|---|
| Team box stats for every completed 2026 FBS game | `pull_box.py` | `box2026.parquet` |
| One row per team-game (points, yards/play, 3rd down, turnovers) | `model.py` | `teamgames.parquet` |
| Opponent-adjusted team-level ratings; VT defense game by game | `fit.py` | `vt_def_games.csv` |
| ESPN play-by-play for every game (downloads raw summaries) | `pbp_all.py` | `pbp2026.parquet` |
| Opponent-adjusted success / explosive / sack rates | `fit2.py` | `vt_def_pbp.csv` |
| Every drive: offense, defense, site, start yard line, points | `drives.py` | `drives2026.parquet` |
| Points per drive cleaned up | `ep.py` | `drives_ep.parquet` |
| Expected points by starting field position (isotonic) | `ep3.py` | `ep_curve.csv`, `drives_ep.parquet` |
| VT defense: actual vs. expected points, leaving each game out | `vtdef.py` | `vt_def_drive_ep.csv` |
| Projections vs. VT's remaining opponents | `predict.py` | printed |
| Venues geocoded, domes flagged | `venues.py` | `venues.csv`, `game_venues.csv` |
| Nearest airport station, hourly weather download | `wx.py` | `asos/<station>.csv`, `venues.csv` |
| Weather from kickoff to +3.5 h per game | `gamewx.py` | `game_weather.csv` |
| Weather terms added to the drive model | `wxfit.py` | `drives_wx.parquet` |

Refresh after a new week: `python ../espn.py 2026 --force`, then rerun the pipeline from
`pull_box.py` (the weather steps only need `venues.py` again if a new venue appears).

## Model

- **Drives.** A drive's start is its first snap's `yardsToEndzone`. ESPN lists a kickoff as the
  first play of a drive at the kicking spot (65 to go), so kickoff plays are skipped. Points count
  only when the offense's own score went up on the drive: ESPN sometimes marks a drive "TD" when
  the defense or return team scored. With both fixes, VT's opponents' drive points match the
  official finals and Clemson's 11 drive starts match the official box.
- **Late drives.** Drives starting with 60 seconds or less left in a half, and overtime drives,
  are excluded from fitting and from game comparisons (kneels and Hail Marys).
- **Expected points curve.** Isotonic (non-increasing in yards to go) fit of points on start
  position over FBS-vs-FBS drives; it preserves the overall mean. About 2.0 points from your own
  25, 2.9 from midfield, 4.0 from the opponent's 30.
- **Team adjustment.** Each drive's points minus its expected points are fit (ridge, lambda 40)
  to offense + defense + home field. A game's expectation = sum over the opponent's actual drives
  of (curve value + offense rating + home field), i.e. against an average FBS defense. So drive
  count (time of possession) and field position are both built in. VT games are scored leaving
  that game out.
- **Weather.** Nearest still-reporting ASOS station (median 7 km) from the IEM network lists;
  average sustained wind and max gust (mph), precipitation, share of observations with rain or
  storms, and mean temperature from 30 minutes before kickoff to 3.5 hours after. Named domes are
  calm and dry; the Ireland and London games have no weather. Terms: rain share, wind above
  10 mph, temperature below 50 F.

## Findings so far (2026 through Oct 24)

- Rain costs about 0.4 points per drive for a game with rain throughout (about 2 SE).
- Wind has no measurable effect below about 20 mph. Points per drive by wind band: 0-5 mph 2.34,
  5-10 2.20, 10-15 2.36, 15-20 2.27, 20+ 1.84 (only 5 games). A threshold term needs more
  seasons (2023-2025) to estimate.
- VT at Boston College (Sept 26) was the windiest game of the season: 30 mph sustained, gusts to
  45, rain throughout. Treat it as an outlier when rating VT's defense.
- Cold is untestable so far (almost no games below 50 F through October).
