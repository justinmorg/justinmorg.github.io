"""Fetch every FBS game's result (and optionally the closing spread) from ESPN's public API.

No key and no monthly quota, so this is the fallback when CFBD is out of calls. Feeds elo.py.

Usage:
    python espn.py 2014-2026            # results, all FBS games (incl. FBS vs FCS), regular + post
    python espn.py 2023-2025 --odds     # also closing spreads (one call per game; slower)
    python espn.py 2026 --force         # re-pull a season already on disk

Writes data/espn/games/<season>.parquet and data/espn/odds/<season>.parquet.
Completed past seasons are skipped if present; the current season is always re-pulled.

Notes
  * Scoreboard: site.api.espn.com .../scoreboard?dates=<season>&seasontype=2&week=N&groups=80
    (groups=80 = FBS; a game is included if either team is FBS). Week 1 includes "week 0".
    Postseason is seasontype=3, week=1.
  * Odds: sports.core.api.espn.com .../events/<id>/competitions/<id>/odds. `spread` is the
    HOME team's line (negative = home favored). The first non-live provider is used.
  * fbs flag: ESPN doesn't label division per game, so a team counts as FBS in a season if it
    appears in 6+ games of the FBS scoreboard (FCS opponents show up once or twice).
"""
import datetime, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "espn")
SB = ("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
      "?dates={season}&seasontype={st}&week={wk}&groups=80&limit=400")
ODDS = ("https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/"
        "events/{id}/competitions/{id}/odds")
UA = "vt-football-archive/1.0 (personal research; github.com/justinmorg)"


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(2 * (i + 1))


def parse(ev, season, st, wk):
    c = ev["competitions"][0]
    t = {x["homeAway"]: x for x in c["competitors"]}
    h, a = t["home"], t["away"]
    sc = lambda x: int(x["score"]) if x.get("score") not in (None, "") else None
    done = c["status"]["type"]["completed"]
    return dict(eventId=int(ev["id"]), season=season, seasonType="post" if st == 3 else "regular",
                week=wk, date=ev["date"][:10], neutralSite=bool(c.get("neutralSite")),
                conferenceGame=bool(c.get("conferenceCompetition")), completed=done,
                homeId=int(h["team"]["id"]), homeTeam=h["team"]["location"],
                homePoints=sc(h) if done else None,
                awayId=int(a["team"]["id"]), awayTeam=a["team"]["location"],
                awayPoints=sc(a) if done else None)


def fetch_games(season):
    rows = []
    for st, weeks in ((2, range(1, 17)), (3, range(1, 2))):
        for wk in weeks:
            d = get(SB.format(season=season, st=st, wk=wk))
            rows += [parse(ev, season, st, wk) for ev in d.get("events", []) if ev.get("competitions")]
    g = pd.DataFrame(rows).drop_duplicates("eventId")
    n = pd.concat([g.homeId, g.awayId]).value_counts()
    fbs = set(n[n >= 6].index)
    g["homeFBS"], g["awayFBS"] = g.homeId.isin(fbs), g.awayId.isin(fbs)
    return g.sort_values(["date", "eventId"]).reset_index(drop=True)


def odds_for(eid):
    try:
        d = get(ODDS.format(id=eid))
    except Exception:
        return None
    for it in d.get("items", []):
        name = (it.get("provider") or {}).get("name", "")
        if "live" in name.lower() or it.get("spread") is None: continue
        ml = (it.get("homeTeamOdds") or {}).get("moneyLine")
        return dict(eventId=eid, provider=name, homeSpread=float(it["spread"]),
                    overUnder=it.get("overUnder"), homeMoneyLine=ml,
                    awayMoneyLine=(it.get("awayTeamOdds") or {}).get("moneyLine"))
    return None


def main(argv):
    force, want_odds = "--force" in argv, "--odds" in argv
    span = [a for a in argv if not a.startswith("--")][0]
    lo, hi = (map(int, span.split("-")) if "-" in span else (int(span),) * 2)
    this_year = datetime.date.today().year
    for d in ("games", "odds"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
    for s in range(lo, hi + 1):
        gp = os.path.join(OUT, "games", f"{s}.parquet")
        if force or s >= this_year or not os.path.exists(gp):
            g = fetch_games(s); g.to_parquet(gp, index=False)
            print(f"{s}: {len(g)} games, {g.completed.sum()} completed")
        else:
            g = pd.read_parquet(gp)
        op = os.path.join(OUT, "odds", f"{s}.parquet")
        if want_odds and (force or s >= this_year or not os.path.exists(op)):
            ids = g[g.completed & g.homeFBS & g.awayFBS].eventId.tolist()
            with ThreadPoolExecutor(8) as ex:
                o = [r for r in ex.map(odds_for, ids) if r]
            pd.DataFrame(o).to_parquet(op, index=False)
            print(f"{s}: odds for {len(o)} of {len(ids)} FBS-vs-FBS games")


if __name__ == "__main__":
    main(sys.argv[1:])
