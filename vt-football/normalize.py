"""Build one query-ready play table from the three sources.

Writes
  data/unified/games.parquet          one row per VT game, with the source used for its plays
  data/unified/plays/<season>.parquet  scrimmage plays only (rushes, sacks, passes)

Source priority per game: hokiesports XML > StatCrew text report > CFBD.
The official stat-crew files match the official box scores; CFBD has season-specific
coding problems (see README, "CFBD data quality"), which are repaired here from the play text
for the games that have no stat-crew file.

Play columns
  season, date, gameKey, cfbdGameId, hsGameId, source, opponent, quarter, clockSeconds,
  offense, defense, vtOffense, down, distance, yardsToGoal,
  category   rush | sack | comp | inc | int
  yards      scrimmage yards, NCAA-style: sacks negative, incompletions and interceptions 0
  fumble     True if the play had a fumble (lost or not)
  text

Usage: python normalize.py
"""
import glob, os, re
import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
OUT = os.path.join(D, "unified")
VT = "Virginia Tech"
COLS = ["season", "date", "gameKey", "cfbdGameId", "hsGameId", "source", "opponent", "quarter",
        "clockSeconds", "offense", "defense", "vtOffense", "down", "distance", "yardsToGoal",
        "category", "yards", "fumble", "text"]


def q(sql):
    return duckdb.sql(sql).df()


# ---------------------------------------------------------------- games
def load_games():
    cf = q(f"""select id cfbdGameId, season, startDate, homeTeam, awayTeam, homePoints, awayPoints, neutralSite
               from read_parquet('{D}/games/*.parquet') where completed""")
    # CFBD start times are UTC; kickoffs after 7pm Eastern land on the next UTC day.
    cf["date"] = (pd.to_datetime(cf.startDate, utc=True) - pd.Timedelta(hours=5)).dt.strftime("%Y-%m-%d")
    cf["vtHome"] = cf.homeTeam.eq(VT)
    cf["opponent"] = np.where(cf.vtHome, cf.awayTeam, cf.homeTeam)
    cf["vtPoints"] = np.where(cf.vtHome, cf.homePoints, cf.awayPoints)
    cf["oppPoints"] = np.where(cf.vtHome, cf.awayPoints, cf.homePoints)

    hs = q(f"select gameId hsGameId, season, date, home, away, homePoints, awayPoints "
           f"from read_parquet('{D}/hokiesports/games/*.parquet')")
    st = q(f"select gameId stGameId, cfbdGameId, season, date, home, away, homePoints, awayPoints "
           f"from read_parquet('{D}/statcrew_text/games/*.parquet')")
    for t in (hs, st):
        t["vtHome"] = t.home.eq(VT)
        t["opponent"] = np.where(t.vtHome, t.away, t.home)
        t["vtPoints"] = np.where(t.vtHome, t.homePoints, t.awayPoints)
        t["oppPoints"] = np.where(t.vtHome, t.awayPoints, t.homePoints)

    # attach hokiesports IDs to CFBD games by date (+/- 1 day)
    cf["hsGameId"] = None
    used = set()
    for i, g in cf.iterrows():
        d = pd.Timestamp(g.date)
        c = hs[(pd.to_datetime(hs.date) - d).abs() <= pd.Timedelta(days=1)]
        if len(c) == 1:
            cf.at[i, "hsGameId"] = c.hsGameId.iloc[0]; used.add(c.hsGameId.iloc[0])
    st["cfbdGameId"] = st.cfbdGameId.astype("int64")
    cf = cf.merge(st[["cfbdGameId", "stGameId"]], on="cfbdGameId", how="left")

    # hokiesports games with no CFBD game (1987-2000)
    extra = hs[~hs.hsGameId.isin(used)].copy()
    extra["cfbdGameId"] = None; extra["stGameId"] = None; extra["neutralSite"] = None
    cols = ["season", "date", "opponent", "vtHome", "neutralSite", "vtPoints", "oppPoints",
            "cfbdGameId", "hsGameId", "stGameId"]
    g = pd.concat([cf[cols], extra[cols]], ignore_index=True)
    g["cfbdGameId"] = g.cfbdGameId.astype("Int64")
    g["gameKey"] = np.where(g.cfbdGameId.notna(), "cfbd:" + g.cfbdGameId.astype(str), "hs:" + g.hsGameId.astype(str))
    return g.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------- stat-crew plays (XML and text)
def statcrew_plays(path_glob, id_col):
    # A few files (2013 Sun Bowl) key a touchdown and its PAT as one 'X' record; keep the scrimmage part.
    p = q(f"""select gameId, quarter, clockSeconds, offense, defense, down, distance, yardsToGoal,
                     case when type = 'X' then (case when rusher is not null then 'R' else 'P' end) else type end as type,
                     yards, passResult, sackBy, fumbleBy, text
              from read_parquet('{path_glob}', union_by_name=true)
              where (type in ('R','P') or (type = 'X' and (rusher is not null or passer is not null)
                                          and text ilike '%touchdown%'))
                and down between 1 and 4""")
    p = p.rename(columns={"gameId": id_col})
    t = p.text.fillna("").str.lower()
    sack = p.passResult.eq("SACK") | p.sackBy.notna() | ((p.type == "P") & t.str.contains("sacked"))
    p["category"] = np.select(
        [sack, p.type.eq("R"), p.passResult.eq("COMP"), p.passResult.eq("INT")],
        ["sack", "rush", "comp", "int"], "inc")
    # a non-sack FUMB pass result is a fumbled snap/exchange on a called pass: count it as a rush
    p.loc[(p.type == "P") & p.passResult.eq("FUMB") & ~sack, "category"] = "rush"
    p["yards"] = np.where(p.category.isin(["inc", "int"]), 0, p.yards.fillna(0))
    # distance 0 means goal to go in these files
    p["distance"] = np.where(p.distance.fillna(0) == 0, p.yardsToGoal, p.distance)
    p["fumble"] = p.fumbleBy.notna()
    return p


# ---------------------------------------------------------------- CFBD plays, repaired
SCRIM = ["Rush", "Rushing Touchdown", "Sack", "Pass", "Pass Completion", "Pass Reception",
         "Passing Touchdown", "Pass Incompletion", "Pass Interception", "Pass Interception Return",
         "Interception", "Interception Return Touchdown", "Fumble Recovery (Own)",
         "Fumble Recovery (Opponent)", "Fumble Return Touchdown"]
YDS_RE = re.compile(r"(?:run|rush(?:ed)?(?: [a-z ]+?)?|pass complete to [^,]*?|sacked[^,]*?) for (?:a )?(loss of )?(-?\d+) y")


def text_yards(t):
    m = YDS_RE.search(t)
    if m:
        n = int(m.group(2)); return -abs(n) if m.group(1) else n
    return 0


def cfbd_plays():
    types = ",".join(f"'{x}'" for x in SCRIM)
    p = q(f"""select gameId cfbdGameId, period AS quarter, clockSeconds, offense, defense, down, distance,
                     yardsToGoal, playType AS t, yardsGained AS yards, playText AS "text"
              from read_parquet('{D}/plays/*.parquet')
              where playType in ({types}) and down between 1 and 4""")
    x = p.text.fillna("").str.lower()
    fum = p.t.str.startswith("Fumble")
    isint = p.t.str.contains("Interception") | (p.t.isin(["Pass"]) | fum) & x.str.contains("intercepted")
    issack = p.t.eq("Sack") | (~p.t.str.startswith("Rush") & x.str.contains("sacked"))
    isinc = p.t.eq("Pass Incompletion") | (p.t.eq("Pass") & x.str.contains("incomplete"))
    ispass = p.t.str.contains("Pass") | (fum & x.str.contains(" pass "))
    p["category"] = np.select([issack, isint, isinc, ispass], ["sack", "int", "inc", "comp"], "rush")
    # fumble plays carry the return yardage in yardsGained (2014-): take scrimmage yards from the text
    p.loc[fum, "yards"] = x[fum].map(text_yards)
    # sacks recorded as 0 yards (2006-2012, part of 2021) or typed "Pass" (2005): loss is in the text
    loss = x.str.extract(r"loss of (\d+)")[0].astype(float)
    fix = issack & (p.yards >= 0) & loss.notna()
    p.loc[fix, "yards"] = -loss[fix]
    # interceptions: return yards were credited to the offense in 2005
    p.loc[p.category.isin(["inc", "int"]), "yards"] = 0
    p["fumble"] = fum | x.str.contains("fumble")
    return p


# ---------------------------------------------------------------- build
def main():
    games = load_games()
    hs = statcrew_plays(f"{D}/hokiesports/plays/*.parquet", "hsGameId")
    st = statcrew_plays(f"{D}/statcrew_text/plays/*.parquet", "stGameId")
    cf = cfbd_plays()

    have_hs, have_st, have_cf = set(hs.hsGameId), set(st.stGameId), set(cf.cfbdGameId)
    games["source"] = [
        "hokiesports" if r.hsGameId in have_hs else
        "statcrew_text" if r.stGameId in have_st else
        "cfbd" if r.cfbdGameId in have_cf else None
        for r in games.itertuples()]

    parts = []
    for src, df, key in (("hokiesports", hs, "hsGameId"), ("statcrew_text", st, "stGameId"),
                         ("cfbd", cf, "cfbdGameId")):
        gsel = games[games.source == src][["season", "date", "gameKey", "cfbdGameId", "hsGameId",
                                           "stGameId", "opponent"]]
        df = df.copy(); df[key] = df[key].astype(gsel[key].dtype)
        m = df.merge(gsel, on=key)
        m["source"] = src
        parts.append(m)
    plays = pd.concat(parts, ignore_index=True)
    plays["vtOffense"] = plays.offense.eq(VT)
    plays["hsGameId"] = plays.hsGameId.astype("string")
    plays = plays[COLS].sort_values(["date", "quarter", "clockSeconds"], ascending=[True, True, False],
                                    kind="stable")

    os.makedirs(os.path.join(OUT, "plays"), exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "plays", "*.parquet")): os.remove(f)
    for season, d in plays.groupby("season"):
        d.to_parquet(os.path.join(OUT, "plays", f"{season}.parquet"), index=False)
    games["hsGameId"] = games.hsGameId.astype("string"); games["stGameId"] = games.stGameId.astype("string")
    games[["season", "date", "gameKey", "opponent", "vtHome", "neutralSite", "vtPoints", "oppPoints",
           "cfbdGameId", "hsGameId", "stGameId", "source"]].to_parquet(os.path.join(OUT, "games.parquet"), index=False)

    s = games.groupby(["season", "source"], dropna=False).size().unstack(fill_value=0)
    print(s.to_string())
    print(f"{len(plays)} plays, {games.source.notna().sum()} of {len(games)} games with play-by-play")


if __name__ == "__main__":
    main()
