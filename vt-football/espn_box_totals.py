"""ESPN team box totals for VT games that have no official stat-crew box in the repo.

The CFBD-sourced games (2001 on) have no hokiesports XML/WMT totals to validate against.
ESPN's game summary box matches the official stat-crew totals exactly where both exist
(checked on 2010 Boise State, James Madison, East Carolina: rush att/yds incl. sacks, pass
att/yds), so validate_box.py uses it as the box for those games.

Usage:
    python espn_box_totals.py           # games in data/unified/games.parquet not from hokiesports
    python espn_box_totals.py --force   # re-pull every game

Writes data/espn/box_totals.csv: cfbdGameId (= ESPN event id), vtOffense, rush_att, rush_yds,
pass_att, pass_yds, ints. ESPN's team box has no sack count, so sacks aren't checked here.
Games ESPN has no box for (2001 Gator Bowl, 2003 Insight Bowl, 2002 West Virginia) are left out.
"""
import os, sys
import pandas as pd
from espn import get, HERE

OUT = os.path.join(HERE, "data", "espn", "box_totals.csv")
SUM = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={}"
VT = "Virginia Tech"


def one(eid):
    d = get(SUM.format(eid))
    rows = []
    for t in d.get("boxscore", {}).get("teams", []):
        st = {s["name"]: s.get("displayValue") for s in t.get("statistics", [])}
        if "rushingAttempts" not in st:
            continue
        att = st["completionAttempts"].replace("-", "/").split("/")[1]
        rows.append(dict(cfbdGameId=eid, vtOffense=t["team"]["location"] == VT,
                         rush_att=int(st["rushingAttempts"]), rush_yds=int(st["rushingYards"]),
                         pass_att=int(att), pass_yds=int(st["netPassingYards"]),
                         ints=int(st.get("interceptions") or 0)))
    return rows


if __name__ == "__main__":
    g = pd.read_parquet(os.path.join(HERE, "data", "unified", "games.parquet"))
    ids = [int(x) for x in g[(g.source != "hokiesports") & g.cfbdGameId.notna()].cfbdGameId]
    old = pd.read_csv(OUT) if os.path.exists(OUT) and "--force" not in sys.argv else pd.DataFrame()
    have = set(old.cfbdGameId) if len(old) else set()
    new = [r for e in ids if e not in have for r in one(e)]
    out = pd.concat([old, pd.DataFrame(new)], ignore_index=True)
    out = out[out.cfbdGameId.isin(ids)].sort_values(["cfbdGameId", "vtOffense"])
    out.to_csv(OUT, index=False)
    print(f"{out.cfbdGameId.nunique()} of {len(ids)} games with an ESPN box -> {os.path.relpath(OUT, HERE)}")
