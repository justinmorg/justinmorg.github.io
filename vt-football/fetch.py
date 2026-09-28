"""Fetch Virginia Tech games, drives, and play-by-play from CollegeFootballData.

Usage:
    export CFBD_API_KEY=...        # never commit the key
    python fetch.py 2001-2025      # backfill a range
    python fetch.py 2026           # refresh one season (current season: re-pull)
    python fetch.py 2026 --force   # re-pull even if files exist

Writes one Parquet file per season per table under data/{games,drives,plays}/.
Completed past seasons are skipped if already present, unless --force.
CFBD play-by-play coverage starts in 2001.
"""
import os, sys, time, datetime, requests
import pandas as pd

TEAM = "Virginia Tech"
BASE = "https://api.collegefootballdata.com"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
S = requests.Session()
S.headers["Authorization"] = f"Bearer {os.environ['CFBD_API_KEY']}"

def get(path, **params):
    for attempt in range(4):
        r = S.get(BASE + path, params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1)); continue
        r.raise_for_status()
        rem = r.headers.get("x-calllimit-remaining")
        if rem and int(rem) < 50:
            print(f"  warning: only {rem} CFBD calls left this month")
        return r.json()
    raise RuntimeError(f"rate limited: {path} {params}")

def clock_secs(d):
    return None if not isinstance(d, dict) else (d.get("minutes") or 0) * 60 + (d.get("seconds") or 0)

def save(df, table, season):
    os.makedirs(os.path.join(DATA, table), exist_ok=True)
    df.to_parquet(os.path.join(DATA, table, f"{season}.parquet"), index=False)

def fetch_season(season, force=False):
    current = season >= datetime.date.today().year
    if not force and not current and os.path.exists(os.path.join(DATA, "plays", f"{season}.parquet")):
        print(f"{season}: already stored, skipping"); return
    games = pd.DataFrame(get("/games", year=season, team=TEAM, seasonType="both"))
    if games.empty:
        print(f"{season}: no games"); return
    for c in ("homeLineScores", "awayLineScores"):
        games[c] = games[c].apply(lambda v: None if v is None else list(v))
    save(games, "games", season)

    drives = pd.DataFrame(get("/drives", year=season, team=TEAM, seasonType="both"))
    if not drives.empty:
        for c in ("startTime", "endTime", "elapsed"):
            drives[c + "Seconds"] = drives.pop(c).apply(clock_secs)
        save(drives, "drives", season)

    done = games[games["completed"]]
    plays = []
    for (stype, week), _ in done.groupby(["seasonType", "week"]):
        p = get("/plays", year=season, week=int(week), seasonType=stype, team=TEAM)
        plays.extend(p)
    plays = pd.DataFrame(plays)
    if not plays.empty:
        plays["clockSeconds"] = plays.pop("clock").apply(clock_secs)
        plays = plays.merge(games[["id", "season", "week", "seasonType"]].rename(columns={"id": "gameId"}),
                            on="gameId", how="left")
        plays = plays.sort_values(["gameId", "driveNumber", "playNumber"])
        save(plays, "plays", season)
    print(f"{season}: {len(games)} games ({len(done)} completed), {len(drives)} drives, {len(plays)} plays")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    for a in args:
        lo, _, hi = a.partition("-")
        for s in range(int(lo), int(hi or lo) + 1):
            fetch_season(s, force)
