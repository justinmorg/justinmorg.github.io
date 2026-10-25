"""Game-phase splits: first half / first two drives of the second half / the rest of the second half.

Built for the 2026 question of whether VT's offense stalls coming out of halftime (Oct. 2026:
VT's first two second-half drives ran ~30% success vs ~45% the rest of the game in FBS games).

    python phase_splits.py                 # VT, every season in data/unified/
    python phase_splits.py --league 2026   # every team in data/espn/league_pbp/2026.parquet

Writes counts (not rates), so any grouping of games re-aggregates exactly:
    data/derived/phase_splits_by_game.csv           VT: one row per game x side x phase
    data/derived/phase_splits_league_<season>.csv   one row per team x game x side x phase

Columns: plays, successes, yards, runs, sacks, explosives, firstDowns (1st-down plays),
firstDownRuns, plus oppFBS (VT file) / offFBS+defFBS (league file) for filtering.
side = off (team's offense) or def (team's defense, opponents' plays).
phase = 1H | 2H_d1-2 | 2H_d3+ ; a second-half drive is any drive whose first scrimmage play is in
Q3 or later, numbered in order for that offense. Overtime is excluded.

Success: >= 50% of distance on 1st down, 70% on 2nd, 100% on 3rd/4th; never on an interception.
Explosive: rush >= 12 or pass >= 16 yards. Sacks count as pass plays; runs = category 'rush'.

Drives in data/unified/ have no id, so a VT drive = a run of consecutive scrimmage plays by the
same offense. Two drives by one team with no opponent scrimmage play between them (e.g. a
turnover returned for a TD, or a muffed punt) merge into one; this is rare.
"""
import glob, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DER = os.path.join(HERE, "data", "derived")


def flags(p):
    if "success" not in p:
        need = np.select([p.down == 1, p.down == 2], [0.5, 0.7], 1.0) * p.distance
        p["success"] = (p.yards >= need) & (p.category != "int")
    if "explosive" not in p:
        p["explosive"] = np.where(p.category == "rush", p.yards >= 12, p.yards >= 16)
    p["run"] = p.category == "rush"
    p["sack"] = p.category == "sack"
    p["firstDown"] = p.down == 1
    p["firstDownRun"] = p.firstDown & p.run
    return p


def phase(p, game, off, drive):
    """p sorted in game order; drive = drive id within game."""
    first_q = p.groupby([game, off, drive]).quarter.transform("min")
    h2 = p[first_q >= 3][[game, off, drive]].drop_duplicates()
    h2["n"] = h2.groupby([game, off]).cumcount() + 1
    p = p.merge(h2, on=[game, off, drive], how="left")
    p["phase"] = np.where(p.quarter <= 2, "1H", np.where(p.n <= 2, "2H_d1-2", "2H_d3+"))
    return p[p.quarter <= 4]


AGG = dict(plays=("yards", "size"), successes=("success", "sum"), yards=("yards", "sum"),
           runs=("run", "sum"), sacks=("sack", "sum"), explosives=("explosive", "sum"),
           firstDowns=("firstDown", "sum"), firstDownRuns=("firstDownRun", "sum"))


def vt():
    p = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(HERE, "data/unified/plays/*.parquet")))],
                  ignore_index=True)
    p["ord"] = np.arange(len(p))
    p = p.sort_values(["gameKey", "quarter", "clockSeconds", "ord"], ascending=[True, True, False, True])
    p["drive"] = (p.vtOffense != p.groupby("gameKey").vtOffense.shift()).astype(int).groupby(p.gameKey).cumsum()
    p = phase(flags(p), "gameKey", "vtOffense", "drive")
    p["side"] = np.where(p.vtOffense, "off", "def")
    out = p.groupby(["season", "date", "gameKey", "opponent", "side", "phase"]).agg(**AGG).reset_index()
    # FBS flag for the opponent, from ESPN results where available (2010 on)
    fbs = {}
    for f in glob.glob(os.path.join(HERE, "data/espn/games/*.parquet")):
        g = pd.read_parquet(f)
        for col, fl in (("homeTeam", "homeFBS"), ("awayTeam", "awayFBS")):
            fbs.update({(s, t): v for s, t, v in zip(g.season, g[col], g[fl])})
    alias = {"Pitt": "Pittsburgh", "App State": "Appalachian State"}
    out["oppFBS"] = [fbs.get((s, o), fbs.get((s, alias.get(o)))) for s, o in zip(out.season, out.opponent)]
    path = os.path.join(DER, "phase_splits_by_game.csv")
    out.to_csv(path, index=False)
    print(f"VT: {out.gameKey.nunique()} games -> {os.path.relpath(path, HERE)}")


def league(season):
    p = pd.read_parquet(os.path.join(HERE, "data/espn/league_pbp", f"{season}.parquet"))
    p = phase(flags(p), "gameId", "offense", "drive")
    rows = []
    for side, team, opp in (("off", "offense", "defense"), ("def", "defense", "offense")):
        g = p.groupby([team, opp, "gameId", "date", "offFBS", "defFBS", "phase"]).agg(**AGG).reset_index()
        rows.append(g.rename(columns={team: "team", opp: "opponent"}).assign(side=side))
    out = pd.concat(rows, ignore_index=True)
    path = os.path.join(DER, f"phase_splits_league_{season}.csv")
    out.to_csv(path, index=False)
    print(f"{season}: {out.team.nunique()} teams -> {os.path.relpath(path, HERE)}")


if __name__ == "__main__":
    if "--league" in sys.argv:
        league(int(sys.argv[sys.argv.index("--league") + 1]))
    else:
        vt()
