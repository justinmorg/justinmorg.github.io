"""Drive table + venue/kickoff table for one or more seasons, straight from ESPN game summaries.

    python season_drives.py 2021 2022 2023 2024 2025 2026
    python season_drives.py 2026 --force       # re-pull every game (e.g. after a new week)

Each summary (~0.5 MB) is parsed in memory and discarded, so no raw JSON is kept on disk.
Writes drives/<season>.parquet (one row per drive, same columns as drives2026.parquet) and
drives/games_<season>.csv (eid, kickoff UTC, venue id/name/city/state/country).
Resumes: games already in the season's files are skipped unless --force. Full seasons:
regular season, conference championships and bowls/CFP (everything ESPN lists as completed).
"""
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import sys, json, pandas as pd
from concurrent.futures import ThreadPoolExecutor
import dm

args = [a for a in sys.argv[1:] if not a.startswith("--")]; force = "--force" in sys.argv
os.makedirs("drives", exist_ok=True)
for season in map(int, args):
    g = dm.games(season)
    dp, gp = f"drives/{season}.parquet", f"drives/games_{season}.csv"
    D0 = pd.read_parquet(dp) if os.path.exists(dp) and not force else pd.DataFrame()
    G0 = pd.read_csv(gp) if os.path.exists(gp) and not force else pd.DataFrame()
    have = set(G0.eid) if len(G0) else set()
    todo = [e for e in g.index if e not in have]
    print(season, "games", len(g), "to pull", len(todo), flush=True)

    def one(eid):
        try:
            s = json.loads(dm.fetch(eid))       # parsed in memory; raw bytes dropped here
            return dm.drives_from_summary(s, g), dm.venue_from_summary(s)
        except Exception as e:
            print("fail", eid, repr(e)[:120], flush=True); return None

    drows, grows = [], []
    for i in range(0, len(todo), 200):          # checkpoint every 200 games
        with ThreadPoolExecutor(10) as ex:
            for r in ex.map(one, todo[i:i + 200]):
                if r: drows += r[0]; grows.append(r[1])
        D = pd.concat([D0, pd.DataFrame(drows)], ignore_index=True)
        G = pd.concat([G0, pd.DataFrame(grows)], ignore_index=True)
        D.to_parquet(dp); G.to_csv(gp, index=False)
        print(f"  {min(i + 200, len(todo))}/{len(todo)}", flush=True)
    D = pd.read_parquet(dp)
    nod = sorted(set(g.index) - set(D.eid))
    print(season, "drives", len(D), "games with drives", D.eid.nunique(), "games without drive data", len(nod))
