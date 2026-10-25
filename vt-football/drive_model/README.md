# Drive model: expected points, defense vs. expectation, weather (2021-2026)

Built Oct 25, 2026 to judge VT's defense against expectation and project the rest of the
season; extended the same day to 2021-2026 to measure weather. Every script runs from this
folder (each one `chdir`s here). Sources are ESPN's public game summaries (no key) and Iowa
Environmental Mesonet airport observations (no key); no CFBD.

## Multi-season weather pipeline (current)

| Step | Script | Output (committed) |
|---|---|---|
| Drive table + venue/kickoff per season; summaries parsed in memory, never saved | `season_drives.py 2021 ... 2026` | `drives/<season>.parquet`, `drives/games_<season>.csv` |
| Venues geocoded (retries, second pass), domes and retractable roofs flagged | `venues.py` | `venues.csv`, `game_venues.csv` |
| Up to 3 candidate airport stations per venue; hourly obs per station-season | `wx.py [seasons]` | `venues.csv` (+ `asos/`, gitignored, ~60 MB) |
| Weather from 30 min before kickoff to +3.5 h | `gamewx.py` | `game_weather.csv` |
| Per-season curve + ratings; pooled weather fit with bootstrap | `wxpool.py` | `ep_curves.csv`, `team_ratings.csv`, `game_resid.csv`, `wx_effects.csv`, `wx_bands.csv` |
| VT 2026 defense re-scored with the pooled weather terms | `vtwx.py` | `vt_def_wx.csv` |

Shared code (drive parser, cleanup, curve, ratings) is in `dm.py`. Refresh after a week:
`python ../espn.py 2026 --force`, then `season_drives.py 2026 --force`, `venues.py`,
`wx.py 2026`, `gamewx.py`, `wxpool.py`, `vtwx.py`. Seasons covered: everything ESPN lists as
completed, including conference title games, bowls and the CFP. ESPN has no drive data for 48
2021 games, 39 in 2022, 8 in 2023, 18 in 2024, 2 in 2025 (mostly FCS opponents); 1-5 games a
season have no usable weather.

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

## Findings, 2021-2026 (4,293 FBS-vs-FBS games, 95,744 drives)

| Term (pts/drive) | Estimate | Boot SE | 95% range | Games |
|---|---|---|---|---|
| Wind 10-15 mph (vs 0-10) | -0.04 | 0.02 | -0.09 to 0.00 | 715 |
| Wind 15-20 | -0.04 | 0.05 | -0.14 to +0.05 | 173 |
| Wind 20-25 | -0.08 | 0.10 | -0.27 to +0.13 | 33 |
| Wind 25+ | -0.53 | 0.24 | -0.93 to 0.00 | 6 |
| Wind, linear above 8 mph (per mph) | -0.009 | 0.004 | -0.016 to -0.002 | |
| Wind, linear above 15 mph (per mph) | -0.018 | 0.011 | -0.038 to +0.004 | |
| Rain throughout | -0.17 | 0.06 | -0.29 to -0.06 | 217 with rain half the time+ |
| Cold below 40 F | -0.06 | 0.04 | -0.14 to +0.02 | 233 |
| Indoor (vs outdoor calm) | -0.05 | 0.04 | -0.13 to +0.04 | 199 |

0-10 mph: 3,167 games. Raw points per drive by band: 0-10 2.22, 10-15 2.17, 15-20 2.12,
20-25 2.10, 25+ 1.67, indoor 2.24.

- Wind is a slow drag, not a cliff, up to 25 mph: about 0.01 points per drive per mph above
  ~8-10 mph, so a 20 mph game costs ~0.1 per drive (~2.5 points per game for both teams).
- The threshold can't be pinned down: the fit is nearly flat from 8 to 22 mph; bootstrap
  picks 8 mph 61% of the time and 22 mph 25% (the latter driven by a handful of gale games).
- 25+ mph is a real step down but rests on 6 games (BC-VT 2026, OSU-Northwestern and MSU-
  Illinois 2022, Memphis-Tulane 2026, FSU-BC 2023, Northwestern-Illinois 2025).
- Rain is the clearest weather effect (about 3 SE). The 2026-only estimate (0.4) was too big.
- Cold under 40 F trims ~0.06 per drive, not significant.

## VT 2026 defense with the pooled weather terms (`vtwx.py`, VT games left out of the fit)

Boston College (Sept 26; 30 mph, gusts 45, rain throughout): VT allowed 14 on 12 drives against
26.7 expected in calm weather, so -12.7 unadjusted. Weather is worth -4.3 points (linear wind,
SE 1.1) to -8.1 (wind bands, SE 3.5; the 25+ band has only 5 other games), leaving VT -8.6 to
-4.8 points better than expected: still a good game, about a third to two thirds of the raw
margin. Season to date (93 drives): -13.8 points vs expectation unadjusted, -9.8 (linear) or
-5.8 (bands) weather-adjusted; without BC VT's defense is average (-0.01 per drive) either way.
Season defensive rating: -0.10 pts/drive (54th of 138 FBS) unadjusted, -0.07 (56th) linear,
-0.05 (62nd) bands.

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
