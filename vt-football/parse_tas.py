"""Parse TAS/StatCrew football XML (<fbgame>) from statistics.hokiesports.com
into Parquet tables under data/hokiesports/{games,drives,plays,players}/<gameid>.parquet.

Usage:  python parse_tas.py <file.xml> [<file.xml> ...] [--source-id 5295]
Keeps the original XML in hokiesports/raw/ so it can be re-parsed later.
"""
import os, sys, shutil, re
import xml.etree.ElementTree as ET
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "hokiesports")
RAW = os.path.join(HERE, "hokiesports", "raw")

def ytg(spot, poss_code, codes):
    """spot like 'ASU35' / 'VT0' -> yards to goal for the team in possession."""
    m = re.match(r"([A-Z&]+)(\d+)$", spot or "")
    if not m: return None
    side, yd = m.group(1), int(m.group(2))
    return 100 - yd if side == poss_code else yd

def clock_secs(c):
    if not c or ":" not in c: return None
    mm, ss = c.split(":"); return int(mm) * 60 + int(ss)

def parse(path, source_id=None):
    root = ET.parse(path).getroot()
    v = root.find("venue")
    teams = {t.get("vh"): t for t in root.findall("team")}
    code = {vh: t.get("id") for vh, t in teams.items()}
    name = {vh: t.get("name") for vh, t in teams.items()}
    gid = source_id or v.get("gameid")
    date = pd.to_datetime(v.get("date"))
    game = dict(gameId=str(gid), tasGameId=v.get("gameid"), season=date.year if date.month > 2 else date.year - 1,
                date=date.date().isoformat(), home=name["H"], away=name["V"],
                homeCode=code["H"], awayCode=code["V"],
                homePoints=int(teams["H"].find("linescore").get("score")),
                awayPoints=int(teams["V"].find("linescore").get("score")),
                homeLine=teams["H"].find("linescore").get("line"), awayLine=teams["V"].find("linescore").get("line"),
                homeRank=teams["H"].get("rank"), awayRank=teams["V"].get("rank"),
                location=v.get("location"), stadium=v.get("stadium"), attendance=v.get("attend"),
                temp=v.get("temp"), wind=v.get("wind"), weather=v.get("weather"))

    drives = []
    for d in root.iter("drive"):
        r = dict(d.attrib); r["gameId"] = str(gid)
        r["offense"] = name.get(r.get("vh")); drives.append(r)

    plays, clock, drive_idx = [], None, None
    for q in root.find("plays").findall("qtr"):
        qn = int(q.get("number"))
        for el in q:
            if el.tag == "drivestart":
                drive_idx = int(el.get("driveindex").split(",")[0]); clock = el.get("clock")
                continue
            if el.tag != "play": continue
            if el.get("clock"): clock = el.get("clock")
            ctx = (el.get("context") or ",,,").split(",")
            poss_vh = ctx[0]
            new = (el.get("newcontext") or ",,,").split(",")
            r = dict(gameId=str(gid), quarter=qn, clock=clock, clockSeconds=clock_secs(clock),
                     drive=drive_idx, playId=el.get("playid"), offense=name.get(poss_vh),
                     defense=name.get("H" if poss_vh == "V" else "V"),
                     down=int(el.get("down") or 0), distance=int(el.get("togo") or 0), spot=el.get("spot"),
                     yardsToGoal=ytg(el.get("spot"), code.get(poss_vh), code),
                     type=el.get("type"), pcode=el.get("pcode"), first=el.get("first"),
                     scoring=el.get("score") == "Y", turnover=el.get("turnover"),
                     outOfBounds=el.get("ob") == "Y", text=el.get("text"),
                     nextPossession=name.get(new[0]))
            ru, pa = el.find("p_ru"), el.find("p_pa")
            if ru is not None: r.update(rusher=ru.get("name"), yards=int(ru.get("gain") or 0))
            if pa is not None:
                r.update(passer=pa.get("qb"), receiver=pa.get("rcv"), passResult=pa.get("result"))
                if pa.get("gain"): r["yards"] = int(pa.get("gain"))
            for tag, key in (("p_pu", "punter"), ("p_ko", "kicker"), ("p_pr", "puntReturner"),
                             ("p_kr", "kickReturner"), ("p_fg", "fgKicker"), ("p_pat", "patKicker")):
                e = el.find(tag)
                if e is not None:
                    r[key] = e.get("name")
                    if tag in ("p_pu", "p_ko", "p_fg"): r[key + "Yards"] = e.get("gain") or e.get("dist")
                    if tag in ("p_fg", "p_pat"): r[key + "Result"] = e.get("result")
            tk = el.findall("p_tk")
            r["tacklers"] = ";".join(t.get("name") for t in tk) or None
            r["sackBy"] = ";".join(t.get("name") for t in tk if t.get("sack") == "Y") or None
            pn = el.findall("p_pn")
            r["penalties"] = ";".join(f"{p.get('vh')}:{p.get('type')}:{p.get('result')}:{p.get('yards') or ''}" for p in pn) or None
            f = el.find("p_fumb")
            if f is not None: r.update(fumbleBy=f.get("name"), fumbleRecoveredBy=f.get("frname"))
            ir = el.find("p_ir")
            if ir is not None: r.update(interceptedBy=ir.get("name"), intReturnYards=ir.get("gain"))
            plays.append(r)

    players = []
    for vh, t in teams.items():
        for p in t.findall("player"):
            base = dict(gameId=str(gid), team=name[vh], name=p.get("name"), uni=p.get("uni"),
                        started=p.get("gs") == "1", offPos=p.get("opos"), defPos=p.get("dpos"))
            for stat in p:
                for k, val in stat.attrib.items():
                    base[f"{stat.tag}_{k}"] = val
            players.append(base)

    for tbl, rows in (("games", [game]), ("drives", drives), ("plays", plays), ("players", players)):
        os.makedirs(os.path.join(OUT, tbl), exist_ok=True)
        pd.DataFrame(rows).to_parquet(os.path.join(OUT, tbl, f"{gid}.parquet"), index=False)
    os.makedirs(RAW, exist_ok=True)
    dest = os.path.join(RAW, f"{gid}.xml")
    if os.path.abspath(path) != os.path.abspath(dest): shutil.copy(path, dest)
    print(f"{gid}: {game['date']} {game['away']} {game['awayPoints']} @ {game['home']} {game['homePoints']} "
          f"- {len(plays)} plays, {len(drives)} drives, {len(players)} players")

if __name__ == "__main__":
    args, sid = sys.argv[1:], None
    if "--source-id" in args:
        i = args.index("--source-id"); sid = args[i + 1]; del args[i:i + 2]
    for a in args: parse(a, sid)
