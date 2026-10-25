# Drive model: expected points, defense vs. expectation, weather (2026)

Built Oct 25, 2026 to judge VT's defense against expectation and project the rest of the
season. Every script runs from this folder (each one `chdir`s here). Sources are ESPN's public
game summaries (no key) and Iowa Environmental Mesonet airport observations (no key); no CFBD.

Raw downloads are gitignored and re-created by the scripts: `espn_pbp/raw/` (ESPN summaries,
~280 MB for one season) and `asos/` (hourly airport observations, ~8 MB).

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
