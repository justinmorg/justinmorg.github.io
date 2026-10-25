"""Scrimmage play-by-play for any FBS team (or every FBS game in a season) from ESPN's public
game summaries. For comparisons beyond VT: national rankings, other coaches' programs.

    python espn_league_pbp.py 2026                       # every completed game with an FBS team
    python espn_league_pbp.py 2014-2025 --team "Penn State"
    python espn_league_pbp.py 2026 --force               # re-pull a file already on disk

Game lists come from data/espn/games/<season>.parquet (run espn.py first for new weeks).
Writes one compact table per season, no raw JSON (a full season of summaries is ~1 GB):
    data/espn/league_pbp/<season>.parquet                 (all games)
    data/espn/team_pbp/<team-slug>/<season>.parquet       (--team)

One row per scrimmage play (downs 1-4, penalties and no-plays dropped), parsed with
espn_pbp.parse so columns match the interim VT tables: offense, defense, drive (ESPN drive
order within the game), quarter, clockSeconds, down, distance, yardsToGoal, plus
  category  rush / sack / comp / inc / int  (fumble-recovery plays go by their text)
  yards     ESPN statYardage; 0 on incompletions and interceptions
  success   >= 50% of distance on 1st down, 70% on 2nd, 100% on 3rd/4th; never on an interception
  explosive rush >= 12 or pass >= 16 yards
  offFBS/defFBS  the espn.py FBS flag for each side
Team names are ESPN locations (Pittsburgh -> Pitt, as in espn_pbp.py).
ESPN play data is less exact than the stat-crew files (a few yards off on some plays, occasional
duplicate plays); compare a team with itself, not ESPN numbers with data/unified/ numbers.
"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
from espn import get, HERE
from espn_pbp import parse, SUM

OUT = os.path.join(HERE, "data", "espn")


def seasons(arg):
    a, _, b = arg.partition("-")
    return list(range(int(a), int(b or a) + 1))


def scrimmage(p):
    p = p[(p.type.isin(["R", "P"])) & p.down.between(1, 4) & ~p.penalty].copy()
    p["category"] = np.where(p.type == "R", "rush",
                    p.passResult.str.lower().fillna("comp"))
    p.loc[p.category.isin(["inc", "int"]), "yards"] = 0
    p = p[p.quarter <= 5].drop_duplicates(["quarter", "clockSeconds", "offense", "text"])
    need = np.select([p.down == 1, p.down == 2], [0.5, 0.7], 1.0) * p.distance
    p["success"] = (p.yards >= need) & (p.category != "int")
    p["explosive"] = np.where(p.category == "rush", p.yards >= 12, p.yards >= 16)
    return p


def one(eid):
    try:
        g, p = parse(eid, get(SUM.format(eid)))
    except Exception as e:
        print(f"  {eid}: {e}", file=sys.stderr)
        return None
    p = scrimmage(p)
    p["season"], p["date"] = g.season.iloc[0], g.date.iloc[0]
    return p


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    team = sys.argv[sys.argv.index("--team") + 1] if "--team" in sys.argv else None
    if team: args.remove(team)
    for season in seasons(args[0]):
        g = pd.read_parquet(os.path.join(OUT, "games", f"{season}.parquet"))
        g = g[g.completed & (g.homeFBS | g.awayFBS)]
        if team:
            g = g[(g.homeTeam == team) | (g.awayTeam == team)]
            path = os.path.join(OUT, "team_pbp", team.lower().replace(" ", "-"), f"{season}.parquet")
        else:
            path = os.path.join(OUT, "league_pbp", f"{season}.parquet")
        if os.path.exists(path) and "--force" not in sys.argv:
            have = pd.read_parquet(path, columns=["gameId"]).gameId.nunique()
            if have >= len(g):
                print(f"{season}: {have} games on disk, skipping"); continue
        with ThreadPoolExecutor(8) as ex:
            parts = [p for p in ex.map(one, g.eventId.astype(str)) if p is not None]
        df = pd.concat(parts, ignore_index=True)
        fbs = {**dict(zip(g.homeTeam, g.homeFBS)), **dict(zip(g.awayTeam, g.awayFBS))}
        loc = lambda s: s.replace({"Pitt": "Pittsburgh"}).map(fbs)  # espn.py keeps "Pittsburgh"
        df["offFBS"] = df.offense.map(fbs).fillna(loc(df.offense)).fillna(False).astype(bool)
        df["defFBS"] = df.defense.map(fbs).fillna(loc(df.defense)).fillna(False).astype(bool)
        cols = ["season", "date", "gameId", "offense", "defense", "offFBS", "defFBS", "drive",
                "quarter", "clockSeconds", "down", "distance", "yardsToGoal", "category", "yards",
                "success", "explosive", "text"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df[cols].to_parquet(path, index=False)
        print(f"{season}: {df.gameId.nunique()} games, {len(df)} scrimmage plays -> {os.path.relpath(path, HERE)}")


if __name__ == "__main__":
    main()
