"""Parse VT's official stat-crew data from the WMT stats API (late 2020 on) into data/hokiesports/.

From late 2020, hokiesports.com box scores (/boxscore/<id>) are served by wmt.games instead of
statistics.hokiesports.com XML. The page embeds a WMT game id; the full game is at
  https://api.wmt.games/api/statistics/games/<wmtId>?with[]=actions&with[]=players&with[]=plays&with[]=drives
This script downloads that JSON to hokiesports/raw_wmt/<boxId>.json and writes the same
games/plays/drives tables parse_tas.py writes (same columns where they exist), keyed by the
hokiesports box score id, so normalize.py treats the game as source 'hokiesports'.

Usage:
    python parse_wmt.py 22963            # one or more hokiesports box score ids
    python parse_wmt.py 22963 --force    # re-download

Mapping notes
  * WMT stores one row per action; actions sharing play_by_play_id are one play.
  * Plays whose text ends in "NO PLAY" (accepted penalties) are typed 'E', as in TAS.
  * clock is the snap time from the "(mm:ss)" prefix of the play text (TAS convention);
    WMT's play_time field is the clock after the play.
  * Sack yards come from the play text ('loss of N'); WMT's action yards were off by one on a
    fumbled sack. A rush with no player action (team run) is typed R from its text.
  * type: R rush, P pass, K kickoff, U punt, F field goal, X PAT, E penalty/no play.
    passResult: COMP / INC / INT / SACK (a sack is a sacked or fumbled pass action, or a
    tackle qualified 'sack').
"""
import json, os, re, sys, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "hokiesports", "raw_wmt")
OUT = os.path.join(HERE, "data", "hokiesports")
UA = "vt-football-archive/1.0 (personal research; github.com/justinmorg)"
API = ("https://api.wmt.games/api/statistics/games/{}"
       "?with[]=actions&with[]=players&with[]=plays&with[]=drives")
VT_ORG = 742
# WMT school names -> the team names used elsewhere in the repo (CFBD style)
NAMES = {"Pittsburgh": "Pitt", "Hokies": "Virginia Tech"}
CODES = {"Virginia Tech": "VT"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def wmt_id(box_id):
    html = fetch(f"https://hokiesports.com/boxscore/{box_id}").decode("utf-8", "replace")
    m = re.search(r"wmt\.games/[a-z]+/stats/match/full/(\d+)", html)
    if not m: raise SystemExit(f"no WMT id on boxscore {box_id}")
    return m.group(1)


def load(box_id, force=False):
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, f"{box_id}.json")
    if force or not os.path.exists(path):
        open(path, "wb").write(fetch(API.format(wmt_id(box_id))))
    d = json.load(open(path))
    return d.get("data", d)


def short(name):
    """'Overton, Jr.,Jeffrey' / 'GRUNKEMEYER,ETHAN' -> 'Overton, Jr., J' / 'Grunkemeyer, E'."""
    if not name: return None
    last, _, first = name.rpartition(",")
    if not last: return name.title()
    return f"{last.strip()}, {first.strip()[:1].upper()}" if first.strip() else last.strip()


def secs(c):
    if not c or ":" not in c: return None
    m, s = c.split(":"); return int(m) * 60 + int(s)


def parse(box_id, d):
    comp = {c["schoolId"]: c for c in d["competitors"]}
    tab = {}
    for p in d["plays"]["data"]:
        p = p["play"]
        if p.get("member_org_id") and p.get("name_tabular"):
            tab.setdefault(p["member_org_id"], NAMES.get(p["name_tabular"], p["name_tabular"]))
    tab[VT_ORG] = "Virginia Tech"
    home_org = d["home_school_id"]; away_org = next(s for s in comp if s != home_org)
    home, away = tab[home_org], tab[away_org]
    code = {}  # side letter used in spots, e.g. VT / UP
    for p in d["plays"]["data"]:
        p = p["play"]
        if p.get("side_of_teams_goal") and p.get("context"):
            side = p["context"].split(",")[3][:1]
            org = home_org if side == "H" else away_org
            if p["location"] and p["location"][: len(p["side_of_teams_goal"])] == p["side_of_teams_goal"]:
                if (p["context"].split(",")[3][1:]).lstrip("0") == p["location"][len(p["side_of_teams_goal"]):].lstrip("0"):
                    code.setdefault(org, p["side_of_teams_goal"])

    def line(c):
        per = sorted((s for s in c["teamStats"] if s["period"]), key=lambda s: s["period"])
        return ",".join(str(s["statistic"].get("sScore", s["statistic"].get("sPoints", ""))) for s in per)

    date = pd.Timestamp(d["game_date_utc"]).tz_convert(d.get("local_time_zone") or "America/New_York")
    games = pd.DataFrame([dict(
        gameId=box_id, wmtGameId=d["id"], season=date.year if date.month > 2 else date.year - 1,
        date=date.strftime("%Y-%m-%d"), home=home, away=away,
        homeCode=code.get(home_org), awayCode=code.get(away_org),
        homePoints=comp[home_org]["score"], awayPoints=comp[away_org]["score"],
        location=", ".join(x for x in (d["venue"].get("city"), d["venue"].get("state")) if x),
        stadium=d["venue"].get("name"), attendance=d.get("attendance"))])

    # ---------------------------------------------------------------- plays
    groups = {}
    for p in d["plays"]["data"]:
        p = p["play"]
        groups.setdefault(p["play_by_play_id"], []).append(p)
    rows = []
    for i, (pid, acts) in enumerate(groups.items()):
        a0 = acts[0]; text = a0["play_by_play_text"] or ""
        kinds = [(a["play_action_type"], a["play_action_sub_type"]) for a in acts]
        ctx = (a0["context"] or ",,,").split(",")
        off_org = home_org if ctx[0] == "H" else away_org if ctx[0] == "V" else None
        offense = tab.get(off_org); defense = tab.get(away_org if off_org == home_org else home_org) if off_org else None
        spot_side, spot_n = (ctx[3][:1], int(ctx[3][1:])) if len(ctx) > 3 and ctx[3][1:].isdigit() else (None, None)
        ytg = None if spot_n is None else (100 - spot_n if spot_side == ctx[0] else spot_n)
        m = re.match(r"\((\d\d:\d\d)\)", text); clock = m.group(1) if m else a0["play_time"]
        first = lambda t, s=None: next((a for a in acts if a["play_action_type"] == t and (s is None or a["play_action_sub_type"] == s)), None)
        sack_q = any("sack;" in (a["play_qualifiers"] or "") for a in acts if a["play_action_type"] == "tackle")
        r = dict(gameId=box_id, quarter=a0["period_number"], clock=clock, clockSeconds=secs(clock),
                 drive=a0["game_drive_number"], playId=str(pid), offense=offense, defense=defense,
                 down=int(ctx[1]) if ctx[1].isdigit() else None, distance=int(ctx[2]) if ctx[2].isdigit() else None,
                 spot=a0["location"], yardsToGoal=ytg, type=None, scoring=any(a["scoring_play"] for a in acts),
                 text=text, rusher=None, yards=None, passer=None, receiver=None, passResult=None,
                 tacklers=";".join(short(a["dsp_name"]) for a in acts if a["play_action_type"] == "tackle") or None,
                 sackBy=None, penalties=";".join(f"{a['play_action_sub_type']}" for a in acts if a["play_action_type"] == "penalty") or None,
                 fumbleBy=short((first("fumble") or {}).get("dsp_name")),
                 fumbleRecoveredBy=short((first("fumble", "recovered") or {}).get("dsp_name")),
                 interceptedBy=short((first("interception") or {}).get("dsp_name")),
                 intReturnYards=(first("interception") or {}).get("yards"))
        if "NO PLAY" in text.upper():
            r["type"] = "E"
        elif first("pass"):
            ps = first("pass"); r["type"] = "P"; r["passer"] = short(ps["dsp_name"])
            r["receiver"] = short((first("pass", "receiver") or {}).get("dsp_name"))
            sub = {s for t, s in kinds if t == "pass"}
            if "sacked" in sub or (("fumbled" in sub or sack_q) and "sacked" in text.lower()):
                r["passResult"] = "SACK"; r["yards"] = (first("pass", "sacked") or first("pass", "fumbled"))["yards"]
                lm = re.search(r"sacked for loss of (\d+) yard", text)
                if lm: r["yards"] = -int(lm.group(1))  # the action's yards can be off by one (fumbled sacks)
                r["sackBy"] = r["tacklers"]
            elif "intercepted" in sub: r["passResult"] = "INT"; r["yards"] = 0
            elif "complete" in sub: r["passResult"] = "COMP"; r["yards"] = first("pass", "complete")["yards"]
            elif "fumbled" in sub: r["passResult"] = "FUMB"; r["yards"] = first("pass", "fumbled")["yards"]
            else: r["passResult"] = "INC"; r["yards"] = 0
        elif first("rush"):
            ru = first("rush"); r.update(type="R", rusher=short(ru["dsp_name"]), yards=ru["yards"])
        elif re.search(r"\) (?:[A-Za-z .'-]+ )?rush ", text) and (tm := re.search(r"for (\d+) yards? (gain|loss)|for no gain", text)):
            # team rush with no player action (e.g. a team run on 4th down)
            n = 0 if not tm.group(1) else int(tm.group(1)) * (-1 if tm.group(2) == "loss" else 1)
            r.update(type="R", rusher="TEAM", yards=n)
        elif first("kickoff"): r["type"] = "K"
        elif first("punt"): r["type"] = "U"
        elif first("fieldgoal"): r["type"] = "F"
        elif first("extrapoint") or first("twopoint"): r["type"] = "X"
        elif first("penalty"): r["type"] = "E"
        rows.append(r)
    plays = pd.DataFrame(rows)

    drives = pd.DataFrame([dict(
        gameId=box_id, driveindex=s["drive_number"], team=code.get(s["member_org_id"]), offense=tab.get(s["member_org_id"]),
        vh="H" if s["member_org_id"] == home_org else "V", plays=s["number_of_plays"], yards=s["yards"],
        top=s["time_of_possession"], start_how=s["start_how"], start_qtr=s["start_quarter"],
        start_time=s["start_time"], start_spot=s["start_spot"], end_how=s["end_how"],
        end_qtr=s["end_quarter"], end_time=s["end_time"], end_spot=s["end_spot"])
        for s in (x["summary"] for x in d["drives"]["data"])])

    # match parse_tas.py dtypes (gameId is a string there; mixed types break the union read)
    for df in (games, plays, drives): df["gameId"] = str(box_id)
    games["attendance"] = games.attendance.astype("string")
    plays["drive"] = plays.drive.astype("float64")
    for name, df in (("games", games), ("plays", plays), ("drives", drives)):
        os.makedirs(os.path.join(OUT, name), exist_ok=True)
        df.to_parquet(os.path.join(OUT, name, f"{box_id}.parquet"), index=False)
    return games, plays


def box_totals(d):
    """Official team totals (TAS convention: rushing includes sacks)."""
    home_org = d["home_school_id"]; out = []
    for c in d["competitors"]:
        s = next(x for x in c["teamStats"] if x["period"] == 0)["statistic"]
        out.append(dict(vtOffense=c["schoolId"] == VT_ORG, rush_att=s.get("sRushes", 0), rush_yds=s.get("sRushingYards", 0),
                        pass_att=s.get("sPassAttempts", 0), pass_yds=s.get("sPassYards", 0),
                        ints=s.get("sPassInterceptions", 0), sacks=s.get("sSacksAllowed", 0)))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for b in args:
        g, p = parse(int(b), load(int(b), "--force" in sys.argv))
        print(g.to_string(index=False)); print(p.type.value_counts(dropna=False).to_dict())
