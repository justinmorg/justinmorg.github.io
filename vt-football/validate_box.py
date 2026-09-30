"""Check play-by-play against the official team box scores in the hokiesports XML.

For every game with a stat-crew XML file, sums plays and yards per team from
  (a) the unified table (data/unified/plays), and
  (b) the repaired CFBD plays (normalize.cfbd_plays), where CFBD has the game,
and compares them with the <totals> block of the XML (rush att/yds incl. sacks, pass att/yds,
interceptions, sacks). Prints a per-season summary and writes data/unified/validation.csv.

Usage: python validate_box.py
"""
import glob, os
import xml.etree.ElementTree as ET
import duckdb
import pandas as pd
import normalize as N

VT = N.VT
STATS = ["plays", "yds", "rush_att", "rush_yds", "pass_att", "pass_yds", "ints", "sacks"]


def box_totals():
    rows = []
    for f in glob.glob(os.path.join(N.HERE, "hokiesports", "raw", "*.xml")):
        gid = os.path.basename(f)[:-4]
        teams = ET.parse(f).getroot().findall("team")
        for t in teams:
            tot = t.find("totals"); ru = tot.find("rush").attrib; pa = tot.find("pass").attrib
            r = dict(hsGameId=gid, vtOffense=t.get("name") == VT,
                     rush_att=int(ru["att"]), rush_yds=int(ru["yds"]), pass_att=int(pa["att"]),
                     pass_yds=int(pa["yds"]), ints=int(pa["int"]), sacks=int(pa.get("sacks") or 0))
            r["plays"] = r["rush_att"] + r["pass_att"]; r["yds"] = r["rush_yds"] + r["pass_yds"]
            rows.append(r)
    return pd.DataFrame(rows)


def team_sums(p):
    p = p.assign(rush=p.category.isin(["rush", "sack"]), pas=p.category.isin(["comp", "inc", "int"]))
    g = p.groupby(["hsGameId", "vtOffense"])
    return pd.DataFrame(dict(
        rush_att=g.rush.sum(), rush_yds=g.apply(lambda d: d.yards[d.rush].sum()),
        pass_att=g.pas.sum(), pass_yds=g.apply(lambda d: d.yards[d.category == "comp"].sum()),
        ints=g.apply(lambda d: (d.category == "int").sum()),
        sacks=g.apply(lambda d: (d.category == "sack").sum()))).assign(
        plays=lambda d: d.rush_att + d.pass_att, yds=lambda d: d.rush_yds + d.pass_yds).reset_index()


def compare(label, sums, box, games):
    j = box.merge(sums, on=["hsGameId", "vtOffense"], suffixes=("_box", ""))
    for s in STATS: j["d_" + s] = j[s] - j[s + "_box"]
    j = j.merge(games[["hsGameId", "season", "date", "opponent"]], on="hsGameId")
    j["check"] = label
    s = j.groupby("season").agg(games=("hsGameId", "nunique"), box_yds=("yds_box", "sum"),
                                abs_yds=("d_yds", lambda v: v.abs().sum()),
                                abs_plays=("d_plays", lambda v: v.abs().sum()),
                                d_sacks=("d_sacks", "sum"), d_ints=("d_ints", "sum"))
    s["yds_err_pct"] = (s.abs_yds / s.box_yds * 100).round(1)
    print(f"\n== {label} ==\n{s.drop(columns='box_yds').to_string()}")
    return j


def main():
    box = box_totals()
    games = pd.read_parquet(os.path.join(N.OUT, "games.parquet"))
    uni = duckdb.sql(f"select * from read_parquet('{N.OUT}/plays/*.parquet') where hsGameId is not null").df()
    a = compare("unified vs box", team_sums(uni), box, games)

    cf = N.cfbd_plays()
    cf["cfbdGameId"] = cf.cfbdGameId.astype("Int64")
    cf = cf.merge(games[["cfbdGameId", "hsGameId"]].dropna(), on="cfbdGameId")
    cf["vtOffense"] = cf.offense.eq(VT)
    b = compare("repaired CFBD vs box", team_sums(cf), box, games)

    out = pd.concat([a, b])[["check", "season", "date", "opponent", "hsGameId", "vtOffense"] +
                            [c for s in STATS for c in (s + "_box", "d_" + s)]]
    out.to_csv(os.path.join(N.OUT, "validation.csv"), index=False)


if __name__ == "__main__":
    main()
