"""Parse a StatCrew *text* report (box score header + drive chart + "Play-by-Play Summary")
into the same tables parse_tas.py writes, for games where no <fbgame> XML survives but a
text report does (e.g. an opponent's athletics site).

Usage:
    python parse_statcrew_text.py <report.txt> --game-id 20050103-AU --cfbd-id 250030259 --season 2004 \
        --date 2005-01-03 --visitor "Virginia Tech" --vcode VT --vletter V \
        --home Auburn --hcode AU --hletter A

The report prefixes each snap with "<team letter> <down>-<togo> <spot>" (e.g. "V 1-10 V20");
the letters are the scorer's team initials, given here as --vletter/--hletter.
Writes data/statcrew_text/{games,drives,plays}/<game-id>.parquet using parse_tas.PLAY_COLS.
Not captured: the per-player tables (use the report or the XML games for those).
"""
import argparse, os, re, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "statcrew_text")
sys.path.insert(0, HERE)
from parse_tas import PLAY_COLS  # noqa: E402

SNAP = re.compile(r"^\s+([A-Z]) (\d)-(\d+|G)\s+([A-Z]\d\d)\s+(.*)$")
NEW_UNPREFIXED = re.compile(r"^\S.* (kickoff \d+ yards|kick attempt|pass attempt|rush attempt)")
NARRATIVE = re.compile(r"(wins the toss|will receive|will kick|Bowl\s*$|^\d{4} )")
QTR = re.compile(r"Play-by-Play Summary \((\d)\w\w quarter\)")
CLOCK = re.compile(r"clock (\d\d:\d\d)")
DRIVE_START = re.compile(r"^(?:[A-Z .&'-]+ )?drive start at (\d\d:\d\d) \(\d\w\w\)[.,]?\s*")
ORD = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
HOW = {"Kickoff": "KO", "Punt": "PUNT", "Interception": "INT", "Fumble": "FUMB", "Downs": "DOWNS",
       "Missed FG": "FGA", "*FIELD GOAL": "FG", "*TOUCHDOWN": "TD", "End of half": "HALF", "*SAFETY": "SAF"}


def yards_in(text):
    m = re.search(r"for loss of (\d+) yards?", text)
    if m: return -int(m.group(1))
    m = re.search(r"for (\d+) yards?", text)
    if m: return int(m.group(1))
    if "for no gain" in text: return 0
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path"); ap.add_argument("--game-id", required=True)
    ap.add_argument("--cfbd-id", help="CFBD game id, stored as cfbdGameId for joins to data/games")
    ap.add_argument("--season", type=int, required=True); ap.add_argument("--date", required=True)
    for side in ("visitor", "home"): ap.add_argument(f"--{side}", required=True)
    for k in ("vcode", "hcode", "vletter", "hletter"): ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    gid = a.game_id
    team = {a.vletter: a.visitor, a.hletter: a.home}
    code = {a.vletter: a.vcode, a.hletter: a.hcode}
    vh = {a.vletter: "V", a.hletter: "H"}
    by_code = {a.vcode: a.vletter, a.hcode: a.hletter}
    other = {a.vletter: a.hletter, a.hletter: a.vletter}
    lines = open(a.path, encoding="utf-8").read().splitlines()

    # ---------- game header ----------
    text = "\n".join(lines)
    sq = re.findall(r"^(\S[^.\n]*?)\.{3,}\s+([\d ]+?)\s+-\s+(\d+)", text, re.M)[:2]
    (vname, vline, vpts), (hname, hline, hpts) = sq
    ranks = re.search(r"#(\d+) .+? vs #(\d+) ", text)
    game = dict(gameId=gid, tasGameId=None, season=a.season, date=a.date, home=a.home, away=a.visitor,
                homeCode=a.hcode, awayCode=a.vcode, homePoints=int(hpts), awayPoints=int(vpts),
                homeLine=",".join(hline.split()), awayLine=",".join(vline.split()),
                homeRank=ranks.group(2) if ranks else None, awayRank=ranks.group(1) if ranks else None,
                location=(re.search(r"\(\w+\. \d+, \d{4} at ([^)]+)\)", text) or [None, None])[1],
                stadium=(re.search(r"Stadium: (.+?)\s{2,}", text) or [None, None])[1],
                attendance=(re.search(r"Attendance: (\d+)", text) or [None, None])[1],
                temp=(re.search(r"Temperature: (\S+)", text) or [None, None])[1],
                wind=(re.search(r"Wind: (\S+)", text) or [None, None])[1],
                weather=(re.search(r"Weather: (\S.*)$", text, re.M) or [None, None])[1],
                source="StatCrew text report", cfbdGameId=a.cfbd_id)

    # ---------- drive chart (first "Drive Chart" table, by team) ----------
    drives = []
    in_chart = False
    for ln in lines:
        if "Drive Chart" in ln: in_chart = True; continue
        if in_chart and ("Play-by-Play" in ln): break
        m = re.match(r"^(\S+)\s+(\d\w\w) ([A-Z]\d\d)\s+(\d\d:\d\d)\s+(.+?)\s{2,}([A-Z]\d\d)\s+(\d\d:\d\d)\s+(\S.*?)\s{2,}(\d+)-(-?\d+)\s+(\d\d:\d\d)", ln)
        if in_chart and m and m.group(1) in by_code:
            t = by_code[m.group(1)]
            sp = lambda s: f"{code[s[0]]}{int(s[1:])}"
            drives.append(dict(vh=vh[t], team=m.group(1), plays=m.group(9), yards=m.group(10),
                               top=m.group(11).lstrip("0"), start_how=HOW.get(m.group(5).strip(), m.group(5).strip()),
                               start_qtr=str(ORD[m.group(2)]), start_time=m.group(4), start_spot=sp(m.group(3)),
                               end_how=HOW.get(m.group(8).strip(), m.group(8).strip()), end_time=m.group(7),
                               end_spot=sp(m.group(6)), gameId=gid, offense=team[t]))
    # the chart is grouped by team; order drives chronologically
    drives.sort(key=lambda d: (int(d["start_qtr"]), -int(d["start_time"].replace(":", ""))))
    for i, d in enumerate(drives, 1): d["driveindex"] = str(i)

    # ---------- play-by-play: join wrapped lines into entries ----------
    entries, qtr, drive, cur, started = [], 1, 1, None, False
    for ln in lines[next(i for i, l in enumerate(lines) if l.strip() == "Play-by-Play Summary"):]:
        m = QTR.search(ln)
        if m: qtr = int(m.group(1)); cur = None; continue
        if ln.startswith("-----"):
            drive += 1; cur = None; continue
        if not ln.strip() or "==" in ln or re.match(r"^\s+[A-Z .&'-]+ \d+, [A-Z .&'-]+ \d+\s*$", ln) or "Tiger Football" in ln or re.search(r"#\d+ .* vs #\d+", ln):
            cur = None; continue
        s = SNAP.match(ln)
        if s:
            started = True
            cur = dict(letter=s.group(1), down=int(s.group(2)), togo=s.group(3), spot=s.group(4),
                       text=s.group(5).strip(), qtr=qtr, drive=drive); entries.append(cur); continue
        body = ln.strip()
        if cur is not None and not NEW_UNPREFIXED.match(body) and not NARRATIVE.search(body):
            cur["text"] += " " + body; continue
        cur = dict(letter=None, down=None, togo=None, spot=None, text=body, qtr=qtr, drive=drive,
                   narrative=bool(NARRATIVE.search(body)) or not started)
        entries.append(cur)

    # ---------- entries -> plays ----------
    plays, clock = [], "15:00"
    snaps = [e for e in entries if e["letter"]]
    for i, e in enumerate(entries):
        t = e["text"]
        if e.get("narrative"): continue
        m = DRIVE_START.match(t)
        if m:
            clock = m.group(1); t = t[m.end():]
            if not t: continue
        t = re.sub(r"^\[SHOT\],\s*", "", t); shot = e["text"].find("[SHOT]") >= 0
        c = CLOCK.search(t)
        if c: clock = c.group(1)
        if re.match(r"^(Start of \d\w\w quarter|End of \d\w\w half|[A-Z]{2,} ball on )", t): continue
        # possession: snap letter; kickoff = team kicking (other side of next snap); PAT = scorer
        nxt = next((x for x in entries[i + 1:] if x["letter"]), None)
        prev = next((x for x in reversed(entries[:i]) if x["letter"]), None)
        if e["letter"]: off = e["letter"]
        elif " kickoff " in t: off = other[nxt["letter"]] if nxt else None
        else: off = prev["letter"] if prev else None
        if " kickoff " in t: typ = "K"
        elif re.search(r"(kick attempt|pass attempt|rush attempt)", t) and not e["spot"] or re.search(r"(pass|rush) attempt (failed|good)", t): typ = "X"
        elif t.startswith("Timeout"): typ = "#"
        elif t.startswith("PENALTY") or "NO PLAY" in t: typ = "E"
        elif " field goal attempt" in t: typ = "F"
        elif " punt " in t: typ = "U"
        elif " pass " in t or " sacked " in t: typ = "P"
        elif " rush" in t: typ = "R"
        else: typ = "?"
        spot = e["spot"]
        if typ == "K": spot = f"{off}35"
        if typ == "X" and not spot: spot = f"{other[off]}03"
        ytg = None
        if spot:
            yd = int(spot[1:]); ytg = 100 - yd if spot[0] == off else yd
        down = e["down"] if typ not in ("K", "X") else 1
        dist = (ytg if e["togo"] == "G" else int(e["togo"])) if e["togo"] and typ not in ("K", "X") else 0
        main_part = t.split(", PENALTY")[0]
        r = dict(gameId=gid, quarter=e["qtr"], clock=clock, drive=e["drive"], playId=str(len(plays) + 1),
                 offense=team.get(off), defense=team.get(other.get(off)), down=down, distance=dist,
                 spot=f"{code[spot[0]]}{int(spot[1:]):02d}" if spot else None, yardsToGoal=ytg, type=typ,
                 scoring=bool(re.search(r"TOUCHDOWN|field goal attempt from \d+ GOOD|kick attempt good|attempt good", t)),
                 outOfBounds="out-of-bounds" in t, text=t, shotgun=shot,
                 nextPossession=team.get(nxt["letter"]) if nxt else None)
        r["clockSeconds"] = int(clock[:2]) * 60 + int(clock[3:])
        if "1ST DOWN" in t: r["first"] = "E" if typ == "E" or "PENALTY" in t.split("1ST DOWN")[0] and typ not in ("R", "P") else typ
        if typ == "R":
            r["rusher"] = re.match(r"^(.+?) rush", t).group(1)
            y = yards_in(main_part)
            if y is None:  # e.g. "rush to the VT28, fumble ..." -> derive from the spot
                to = re.search(r"to the ([A-Z]{2,})(\d+)", main_part)
                if to and ytg is not None:
                    end = int(to.group(2)); end_ytg = 100 - end if to.group(1) == code[off] else end
                    y = ytg - end_ytg
            r["yards"] = y
        if typ == "P" or (typ == "E" and " pass " in t):
            pm = re.match(r"^(.+?) (?:pass|sacked)", t)
            if pm: r["passer"] = pm.group(1)
            rc = re.search(r"pass (?:complete|incomplete) to (.+?)(?: for |\.\s*$|\.,|, | \()", t)
            if rc: r["receiver"] = rc.group(1)
            r["passResult"] = ("SACK" if " sacked " in t else "INT" if "intercepted" in t else
                               "COMP" if "pass complete" in t else "INC" if "incomplete" in t else None)
            if typ == "P" and r["passResult"] in ("COMP", "SACK"): r["yards"] = yards_in(main_part)
        if typ == "U":
            pm = re.match(r"^(.+?) punt (\d+) yards", t); r["punter"], r["punterYards"] = pm.group(1), pm.group(2)
            rm = re.search(r"(?:, |fair catch by )([A-Z][^,]*?)(?: return|\.$|,)", t.split(" punt ", 1)[1])
            if rm and ("return" in t or "fair catch" in t): r["puntReturner"] = rm.group(1)
        if typ == "K":
            km = re.match(r"^(.+?) kickoff (\d+) yards", t); r["kicker"], r["kickerYards"] = km.group(1), km.group(2)
            rm = re.search(r", ([A-Z][^,]*?) return", t)
            if rm: r["kickReturner"] = rm.group(1)
        if typ == "F":
            fm = re.match(r"^(.+?) field goal attempt from (\d+) (GOOD|MISSED|BLOCKED)", t)
            r["fgKicker"], r["fgKickerYards"], r["fgKickerResult"] = fm.groups()
        if typ == "X":
            xm = re.match(r"^(.+?) (kick|pass|rush) attempt (good|failed)", t, re.I)
            if xm:
                r["patKicker"] = xm.group(1) if xm.group(2) == "kick" else None
                r["patKickerResult"] = "GOOD" if xm.group(3).lower() == "good" else "MISSED"
                r["patType"] = xm.group(2)
        tk = re.search(r"\(([^()]+)\)\.?$", main_part.strip())
        if tk and typ in ("R", "P", "U", "K") and not (typ == "P" and r.get("passResult") == "INC"):
            r["tacklers"] = tk.group(1)
            if r.get("passResult") == "SACK": r["sackBy"] = tk.group(1)
        if typ == "P" and r.get("passResult") == "INC" and tk: r["passDefender"] = tk.group(1)
        pens = []
        for pm in re.finditer(r"PENALTY ([A-Z]{2,}) ([a-z][a-z ]+?)(?: \(([^)]+)\))?(?: (\d+) yards| declined)", t):
            res = "DECLINE" if pm.group(0).endswith("declined") else "ACCEPT"
            pens.append(f"{vh[by_code[pm.group(1)]]}:{pm.group(2)}:{res}:{pm.group(4) or ''}")
        r["penalties"] = ";".join(pens) or None
        fm = re.search(r"fumble by (.+?) recovered by ([A-Z]{2,}) (.+?) at", t)
        if fm:
            r["fumbleBy"], r["fumbleRecoveredBy"] = fm.group(1), fm.group(3)
            if fm.group(2) != code[off]: r["turnover"] = "F"
        im = re.search(r"intercepted by (.+?) at the \S+ (.+?) return (-?\d+) yards", t)
        if im: r["interceptedBy"], r["intReturnYards"], r["turnover"] = im.group(1), im.group(3), "I"
        plays.append(r)

    df = pd.DataFrame(plays)
    extra = [c for c in df.columns if c not in PLAY_COLS]
    df = df.reindex(columns=PLAY_COLS + extra)
    for tbl, frame in (("games", pd.DataFrame([game])), ("drives", pd.DataFrame(drives)), ("plays", df)):
        os.makedirs(os.path.join(OUT, tbl), exist_ok=True)
        frame.to_parquet(os.path.join(OUT, tbl, f"{gid}.parquet"), index=False)
    unk = df[df.type == "?"]
    print(f"{gid}: {game['date']} {game['away']} {game['awayPoints']} @ {game['home']} {game['homePoints']} "
          f"- {len(df)} plays, {len(drives)} drives" + (f"; {len(unk)} unclassified" if len(unk) else ""))


if __name__ == "__main__":
    main()
