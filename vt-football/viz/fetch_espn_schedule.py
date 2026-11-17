"""VT's schedule from ESPN's public team-schedule endpoint: AP rank at kickoff for both teams,
kickoff time (UTC), line scores, attendance. Fills what the stat-crew/WMT tables lack
(ranks for 2005-2007 and 2020 on, line scores for WMT games). No key needed.

    python viz/fetch_espn_schedule.py 2001 2026   ->  data/espn/vt_schedule.parquet
"""
import json, os, sys, time, urllib.request
import pandas as pd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/259/schedule?season={}&seasontype={}"

def pull(season):
    rows = []
    for st in (2, 3):
        with urllib.request.urlopen(URL.format(season, st), timeout=30) as r:
            j = json.load(r)
        for e in j.get("events", []):
            c = e["competitions"][0]
            vt = next(x for x in c["competitors"] if x["team"]["id"] == "259")
            op = next(x for x in c["competitors"] if x["team"]["id"] != "259")
            if not c.get("status", {}).get("type", {}).get("completed"): continue
            rk = lambda x: (lambda v: None if v in (None, 99, 0) else v)((x.get("curatedRank") or {}).get("current"))
            ls = lambda x: ",".join(str(int(p["value"])) for p in x.get("linescores", [])) or None
            rows.append(dict(season=season, seasonType=st, esGameId=e["id"], dateUTC=e["date"], name=e.get("name"),
                opponent=op["team"].get("location") or op["team"]["displayName"], vtHome=vt["homeAway"] == "home",
                neutral=c.get("neutralSite"), vtPoints=int(vt["score"]["value"]), oppPoints=int(op["score"]["value"]),
                vtRank=rk(vt), oppRank=rk(op), vtLine=ls(vt), oppLine=ls(op), attendance=c.get("attendance"),
                venue=(c.get("venue") or {}).get("fullName"), note=(c.get("notes") or [{}])[0].get("headline")))
        time.sleep(0.3)
    return rows

if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2])
    rows = []
    for s in range(a, b + 1):
        r = pull(s); rows += r; print(s, len(r))
    df = pd.DataFrame(rows).drop_duplicates("esGameId")
    df.to_parquet(os.path.join(HERE, "data", "espn", "vt_schedule.parquet"), index=False)
