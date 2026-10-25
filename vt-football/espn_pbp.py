"""Interim VT play-by-play from ESPN's public game summary, for games whose official stat-crew
data (hokiesports.com / WMT) isn't posted yet.

    python espn_pbp.py 401858276            # one or more ESPN event ids
    python espn_pbp.py 401858276 --force    # re-download

Raw JSON goes to data/espn/pbp/raw/<eventId>.json; tables go to data/espn/pbp/{games,plays}/
in the same column shape as the stat-crew tables, so normalize.py reads them with the same code.
normalize.py ranks this source below hokiesports and StatCrew text and above CFBD, so once the
official WMT game is loaded with parse_wmt.py the ESPN rows drop out of data/unified/ by themselves.

Mapping notes
  * offense/defense come from the play's teamParticipants (falling back to the drive team).
  * clock is the snap time from the "(mm:ss)" prefix of the play text, as in the stat-crew tables.
  * yards = ESPN statYardage (sacks negative). type: R rush, P pass (incl. sacks), K kickoff,
    U punt, F field goal, E penalty / no play; timeouts and period markers are dropped.
  * Fumble-recovery plays are typed R or P from their text.
"""
import json, os, re, sys, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "data", "espn", "pbp")
SUM = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={}"
UA = "vt-football-archive/1.0 (personal research; github.com/justinmorg)"
# ESPN team locations -> the team names used elsewhere in the repo (CFBD style)
NAMES = {"Pittsburgh": "Pitt"}
DROP = {"Timeout", "End Period", "End of Half", "End of Game", "Coin Toss", "Two-minute warning"}


def load(eid, force=False):
    raw = os.path.join(BASE, "raw"); os.makedirs(raw, exist_ok=True)
    path = os.path.join(raw, f"{eid}.json")
    if force or not os.path.exists(path):
        req = urllib.request.Request(SUM.format(eid), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            open(path, "wb").write(r.read())
    return json.load(open(path))


def secs(c):
    if not c or ":" not in c: return None
    m, s = c.split(":"); return int(m) * 60 + int(s)


def ptype(t, text):
    x = text.lower()
    if t in ("Rush", "Rushing Touchdown"): return "R"
    if t == "Sack" or t.startswith("Pass") or "Interception" in t: return "P"
    if t.startswith("Kickoff"): return "K"
    if t.startswith("Punt") or t == "Blocked Punt": return "U"
    if t.startswith("Field Goal") or t == "Blocked Field Goal": return "F"
    if t == "Penalty": return "E"
    if t.startswith("Fumble"):
        return "P" if (" pass " in x or "sacked" in x) else "R"
    return "E"


def parse(eid, s):
    comp = s["header"]["competitions"][0]
    team = {c["id"]: NAMES.get(c["team"]["location"], c["team"]["location"]) for c in comp["competitors"]}
    home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
    away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
    # ESPN dates are UTC; shift to Eastern so night kickoffs keep their local date
    date = (pd.Timestamp(comp["date"]) - pd.Timedelta(hours=5)).strftime("%Y-%m-%d")
    game = dict(gameId=str(eid), season=s["header"]["season"]["year"], date=date,
                home=team[home["id"]], away=team[away["id"]],
                homePoints=int(home["score"]), awayPoints=int(away["score"]),
                source="ESPN game summary (interim)")
    rows = []
    for dn, d in enumerate(s.get("drives", {}).get("previous", []), 1):
        for p in d.get("plays", []):
            t = p.get("type", {}).get("text", "")
            if t in DROP: continue
            text = p.get("text", "")
            off = next((x["id"] for x in p.get("teamParticipants", []) if x.get("type") == "offense"),
                       d.get("team", {}).get("id"))
            dfn = next((i for i in team if i != off), None)
            st = p.get("start", {})
            m = re.match(r"\((\d+:\d\d)\)", text)
            clock = m.group(1) if m else p.get("clock", {}).get("displayValue")
            ty = ptype(t, text)
            x = text.lower()
            sack = t == "Sack" or (ty == "P" and "sacked" in x)
            if ty == "P":
                pr = ("SACK" if sack else "INT" if ("intercept" in x or "Interception" in t)
                      else "INC" if ("incomplete" in x or t == "Pass Incompletion") else "COMP")
            else:
                pr = None
            sm = re.search(r"sacked by ([^(,]+?)(?: for|\s*\(|,|$)", text, re.I)
            rows.append(dict(
                gameId=str(eid), quarter=p["period"]["number"], clock=clock, clockSeconds=secs(clock),
                drive=dn, playId=int(p["sequenceNumber"]), offense=team.get(off), defense=team.get(dfn),
                down=st.get("down") or None, distance=st.get("distance"), yardsToGoal=st.get("yardsToEndzone"),
                type=ty, espnType=t, yards=p.get("statYardage"), passResult=pr,
                sackBy=(sm.group(1).strip() if sm else ("TEAM" if sack else None)),
                fumbleBy=("fumble" if "fumble" in x else None),
                scoring=bool(p.get("scoringPlay")), turnover=bool(p.get("isTurnover")),
                penalty=bool(p.get("isPenalty")), text=text, rusher=None, passer=None))
    plays = pd.DataFrame(rows)
    plays["down"] = plays.down.astype("Int64")
    return pd.DataFrame([game]), plays


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for eid in args:
        g, p = parse(eid, load(eid, "--force" in sys.argv))
        for name, df in (("games", g), ("plays", p)):
            os.makedirs(os.path.join(BASE, name), exist_ok=True)
            df.to_parquet(os.path.join(BASE, name, f"{eid}.parquet"), index=False)
        r = g.iloc[0]
        print(f"{eid}: {r.away} {r.awayPoints} at {r.home} {r.homePoints} ({r.date}), {len(p)} plays")


if __name__ == "__main__":
    main()
