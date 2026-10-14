"""Per-game team turnover stats for every game in data/espn/games/ from ESPN game summaries.

No key, no quota (one call per game). Writes data/espn/box/<season>.parquet with one row per
team per game: eventId, season, seasonType, date, teamId, team, oppId, opp, fbs, oppFbs,
intThrown, fumblesLost, turnovers (as ESPN reports them; turnovers = intThrown + fumblesLost).
A team's takeaways in a game are its opponent's turnovers.

Usage:
    python espn_box.py 2010-2026          # skips completed past seasons already on disk
    python espn_box.py 2026 --force       # re-pull (run espn.py 2026 first for new games)
"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from espn import get, HERE

OUT = os.path.join(HERE, "data", "espn", "box")
SUM = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={id}"


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def one(eid):
    try:
        d = get(SUM.format(id=eid))
    except Exception:
        return eid, None
    out = {}
    for t in d.get("boxscore", {}).get("teams", []):
        st = {s["name"]: s.get("displayValue") for s in t.get("statistics", [])}
        out[int(t["team"]["id"])] = dict(intThrown=num(st.get("interceptions")),
                                         fumblesLost=num(st.get("fumblesLost")),
                                         turnovers=num(st.get("turnovers")))
    return eid, out


def season(y, force=False):
    path = os.path.join(OUT, f"{y}.parquet")
    if os.path.exists(path) and not force:
        print(y, "on disk, skipped"); return
    g = pd.read_parquet(os.path.join(HERE, "data", "espn", "games", f"{y}.parquet"))
    g = g[g.completed]
    with ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(one, g.eventId.tolist()))
    rows, miss = [], 0
    for r in g.itertuples():
        box = res.get(r.eventId)
        if not box or len(box) != 2:
            miss += 1; continue
        for tid, tm, oid, om, f, of in [(r.homeId, r.homeTeam, r.awayId, r.awayTeam, r.homeFBS, r.awayFBS),
                                        (r.awayId, r.awayTeam, r.homeId, r.homeTeam, r.awayFBS, r.homeFBS)]:
            s = box.get(tid)
            if s is None:
                continue
            rows.append(dict(eventId=r.eventId, season=y, seasonType=r.seasonType, date=r.date,
                             teamId=tid, team=tm, oppId=oid, opp=om, fbs=bool(f), oppFbs=bool(of), **s))
    os.makedirs(OUT, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    print(y, f"{len(g)} games, {miss} without a box, {len(rows)} team rows")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    a, _, b = args[0].partition("-")
    for y in range(int(a), int(b or a) + 1):
        season(y, "--force" in sys.argv)
