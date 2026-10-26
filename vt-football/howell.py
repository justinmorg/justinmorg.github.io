"""All Division I-A / FBS game scores by season from James Howell's historical scores.

Source: https://www.jhowell.net/cf/scores/ (one page per team, full history). Used to
opponent-adjust VT's scoring defense before ESPN coverage begins (ESPN's scoreboard API
starts in 2002). No key needed.

Usage:
    python howell.py              # download team pages (cached) and write the game table
    python howell.py --force      # re-download every page

Writes data/howell/games.csv: one row per game, 1987 on. Columns: season, date (m/d),
team, opp, pf, pa, home (1 = team at home, -1 = away, 0 = neutral). Team names are
Howell's page names (e.g. VirginiaTech). Games against non-I-A opponents have
opp = NONIA. I-A vs I-A games appear once. Raw pages go to data/howell/raw/ (gitignored).
The current season isn't on the team pages (it's in Sked<year>.htm); defense_rank.py
takes the current season from data/espn/games/ instead.
"""
import glob, os, re, sys, time, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "howell")
RAW = os.path.join(OUT, "raw")
BASE = "https://www.jhowell.net/cf/scores/"
UA = "vt-football-archive/1.0 (personal research; github.com/justinmorg)"
SKIP = {"ScoresIndex.htm", "byconf.htm", "byname.htm", "notes.htm"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("latin-1")


def download(force=False):
    os.makedirs(RAW, exist_ok=True)
    idx = get(BASE + "byname.htm")
    pages = sorted({p for p in re.findall(r'href="([^"#]+\.htm)"', idx)
                    if p not in SKIP and not p.startswith("Sked") and "/" not in p})
    for p in pages:
        f = os.path.join(RAW, p)
        if os.path.exists(f) and os.path.getsize(f) > 0 and not force:
            continue
        open(f, "w", encoding="latin-1").write(get(BASE + p))
        time.sleep(0.3)
    return len(pages)


def parse(first=1987):
    rows = []
    for f in glob.glob(os.path.join(RAW, "*.htm")):
        team = os.path.basename(f)[:-4]
        html = open(f, encoding="latin-1").read()
        for tbl in html.split("<table")[1:]:
            m = re.search(r"<a name=(\d{4})>", tbl)
            if not m or int(m.group(1)) < first:
                continue
            yr = int(m.group(1))
            for tr in re.findall(r"<tr>(.*?)</tr>", tbl, re.S):
                tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
                if len(tds) < 6 or not re.match(r"\d+/\d+", tds[0].strip()):
                    continue
                try:
                    pf, pa = int(tds[4]), int(tds[5])
                except ValueError:
                    continue  # unplayed / cancelled
                link = re.search(r'href="([^"#]+)\.htm', tds[2])
                opp = link.group(1) if link else "NONIA"
                neutral = len(tds) > 6 and tds[6].strip().startswith("@")
                home = 0 if neutral else (1 if tds[1].strip().startswith("vs") else -1)
                rows.append(dict(season=yr, date=tds[0].strip(), team=team, opp=opp,
                                 pf=pf, pa=pa, home=home))
    df = pd.DataFrame(rows)
    ia = df[(df.opp != "NONIA") & (df.team < df.opp)]  # each I-A game once
    out = pd.concat([ia, df[df.opp == "NONIA"]]).sort_values(["season", "team", "date"])
    return out


if __name__ == "__main__":
    n = download(force="--force" in sys.argv)
    g = parse()
    g.to_csv(os.path.join(OUT, "games.csv"), index=False)
    print(f"{n} team pages; {len(g)} games, {g.season.min()}-{g.season.max()}")
