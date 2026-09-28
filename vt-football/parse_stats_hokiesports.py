"""Save a game-level record from a stats.hokiesports.com box score page.

These pages (https://stats.hokiesports.com/football/box/?<id>=) have a line score, game
details, a scoring summary and team stats, but no play-by-play. Use them as a partial
record for games with no play-by-play anywhere.

Usage:
    python parse_stats_hokiesports.py 5988 [--cfbd-id 223240259] [--html saved.html]

Saves the page to stats_hokiesports/raw/<id>.html (or reads --html) and writes
data/stats_hokiesports/{games,scoring,teamstats}/<id>.parquet.
The site's derived averages are sometimes wrong (e.g. "Average Per Rush 0.0"); they are
stored as published.
"""
import argparse, io, os, re, urllib.request
from datetime import datetime
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "stats_hokiesports", "raw")
OUT = os.path.join(HERE, "data", "stats_hokiesports")
URL = "https://stats.hokiesports.com/football/box/?{id}="
QTRS = {"First": 1, "Second": 2, "Third": 3, "Fourth": 4}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id"); ap.add_argument("--cfbd-id"); ap.add_argument("--html")
    a = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)
    raw = os.path.join(RAW, f"{a.id}.html")
    if a.html: html = open(a.html, encoding="utf-8").read()
    else:
        req = urllib.request.Request(URL.format(id=a.id), headers={"User-Agent": "vt-football-archive/1.0"})
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    with open(raw, "w", encoding="utf-8") as f: f.write(html)

    t = pd.read_html(io.StringIO(html))
    line, details, scoring = t[0], str(t[1].iloc[0, 0]), t[2]
    name_rec = lambda s: re.match(r"^(.*?) \((.*)\)$", s).groups()
    away, away_rec = name_rec(line.iloc[0, 0]); home, home_rec = name_rec(line.iloc[1, 0])
    date_site = line.iloc[2, 0]
    dm = re.match(r"^(\w+ \d+, \d{4})(.*)$", date_site)
    field = lambda k: (re.search(rf"{k}: (.*?)(?=[A-Z][A-Za-z ]+: |$)", details) or [None, None])[1]
    officials = "; ".join(f"{k}: {field(k)}" for k in ("Referee", "Umpire", "Linesman", "Line judge",
                          "Back judge", "Field judge", "Side judge") if field(k))
    game = dict(gameId=a.id, cfbdGameId=a.cfbd_id,
                date=datetime.strptime(dm.group(1), "%B %d, %Y").strftime("%Y-%m-%d"),
                site=dm.group(2).strip(), away=away, home=home, awayRecord=away_rec, homeRecord=home_rec,
                awayPoints=int(line.iloc[0, -1]), homePoints=int(line.iloc[1, -1]),
                awayLine=",".join(str(int(x)) for x in line.iloc[0, 1:-1]),
                homeLine=",".join(str(int(x)) for x in line.iloc[1, 1:-1]),
                kickoff=field("Kickoff time"), endOfGame=field("End of Game"), elapsed=field("Total elapsed time"),
                temp=field("Temperature"), wind=field("Wind"), weather=field("Weather"),
                attendance=(field("Attendance") or "").replace(",", "") or None, officials=officials,
                source="stats.hokiesports.com box score (no play-by-play)")

    rows, qtr, prev = [], None, (0, 0)
    for _, r in scoring.iterrows():
        q = str(r[0]).split()[0]
        if q in QTRS and str(r[3]).endswith("Quarter"): qtr = QTRS[q]; continue
        desc = str(r[3]); d = re.search(r"Drive: (\d+) plays?, (-?\d+) yds", desc)
        score = (int(r[4]), int(r[5]))  # visitor, home after the score
        team = away if score[0] > prev[0] else home if score[1] > prev[1] else None
        rows.append(dict(gameId=a.id, quarter=qtr, clock=r[2], type=r[1], team=team,
                         description=re.sub(r"Drive: .*$", "", desc).strip(),
                         drivePlays=int(d.group(1)) if d else pd.NA, driveYards=int(d.group(2)) if d else pd.NA,
                         awayScore=score[0], homeScore=score[1]))
        prev = score
    stats = pd.concat([x.iloc[1:] for x in t[3:]], ignore_index=True)
    stats.columns = ["stat", "away", "home"]
    stats.insert(0, "gameId", a.id)

    sc = pd.DataFrame(rows).astype({"drivePlays": "Int64", "driveYards": "Int64"})
    for tbl, df in (("games", pd.DataFrame([game])), ("scoring", sc), ("teamstats", stats)):
        os.makedirs(os.path.join(OUT, tbl), exist_ok=True)
        df.astype({c: "string" for c in df.columns if df[c].dtype == object}).to_parquet(
            os.path.join(OUT, tbl, f"{a.id}.parquet"), index=False)
    print(f"{a.id}: {game['date']} {away} {game['awayPoints']} @ {home} {game['homePoints']} - "
          f"{len(rows)} scoring plays, {len(stats)} team stat rows")


if __name__ == "__main__":
    main()
