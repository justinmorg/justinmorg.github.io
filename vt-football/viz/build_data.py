"""Build the JSON behind the visualization pages (vt-football/index.html and viz/*.html).

    python viz/fetch_espn_schedule.py 1999 2026   # AP ranks + kickoff times (after new games)
    python viz/build_data.py                      # -> viz/data/site.json

Everything comes from tables already in the repo:
  data/unified/        games + scrimmage plays (success rate, yards per play, explosives)
  data/howell/         every I-A/FBS score since 1987 (full W-L, Elo-style rating, missing games)
  data/hokiesports/    AP rank at kickoff, attendance, weather, line scores; raw XML/JSON kickoff times
  data/games/          CFBD line scores, attendance (2001-2025)
  data/espn/vt_schedule.parquet   AP ranks 2005 on, kickoff times for CFBD games
  data/derived/        defense rank by season, penalties by game, takeaways
  data/elo/            2026 rating movement (ESPN-based Elo)
Definitions match phase_splits.py: success = 50% of distance on 1st down, 70% on 2nd, 100% on
3rd/4th (never on an interception); explosive = rush >= 12 or pass >= 16 yards.
"""
import glob, json, math, os, re
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *a: os.path.join(HERE, "data", *a)
OUT = os.path.join(HERE, "viz", "data"); os.makedirs(OUT, exist_ok=True)

COACH = lambda s: "Beamer" if s <= 2015 else "Fuente" if s <= 2021 else "Pry" if s <= 2025 else "Franklin"
CONF = lambda s: "Independent" if s <= 1990 else "Big East" if s <= 2003 else "ACC"
BOWLS = {1993: "Independence Bowl", 1994: "Gator Bowl", 1995: "Sugar Bowl", 1996: "Orange Bowl",
         1997: "Gator Bowl", 1998: "Music City Bowl", 1999: "Sugar Bowl (BCS title game)", 2000: "Gator Bowl",
         2001: "Gator Bowl"}
ACCCG = {"2005-12-03", "2007-12-01", "2008-12-06", "2010-12-04", "2011-12-03", "2016-12-03"}
PRETTY = {"Miami(Florida)": "Miami", "NONIA": "Non-I-A opponent", "Alabama-Birmingham": "UAB",
          "CentralFlorida": "UCF", "NorthCarolinaState": "NC State", "SouthernMississippi": "Southern Miss",
          "TexasA&M": "Texas A&M", "Miami(Ohio)": "Miami (OH)"}
pretty = lambda n: PRETTY.get(n, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n))
r1 = lambda x, n=1: None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)

# ---------------------------------------------------------------- games
g = pd.read_parquet(D("unified", "games.parquet")).sort_values("date").reset_index(drop=True)
g["pbp"] = True

# Howell: full schedule, site, missing games
h = pd.read_csv(D("howell", "games.csv"))
md = h.date.str.split("/", expand=True).astype(int)
h["fdate"] = pd.to_datetime(dict(year=h.season + (md[0] <= 2), month=md[0], day=md[1])).dt.strftime("%Y-%m-%d")
hv = h[(h.team == "VirginiaTech") | (h.opp == "VirginiaTech")].copy()
isT = hv.team == "VirginiaTech"
hv["vtPoints"] = np.where(isT, hv.pf, hv.pa); hv["oppPoints"] = np.where(isT, hv.pa, hv.pf)
hv["oppH"] = np.where(isT, hv.opp, hv.team); hv["site"] = np.where(hv.home == 0, "N", np.where((hv.home == 1) == isT, "H", "A"))
site = dict(zip(hv.fdate, hv.site))
have = set(zip(g.season, g.vtPoints, g.oppPoints))
miss = hv[[(s, a, b) not in have for s, a, b in zip(hv.season, hv.vtPoints, hv.oppPoints)]]
OPPFIX = {}
OPPNAME = {"Pitt": "Pittsburgh", "Southern Mississippi": "Southern Miss", "Miami University": "Miami (OH)"}
SITEFIX = {"2002-08-25": "H"}
add = pd.DataFrame(dict(season=miss.season, date=miss.fdate, gameKey="howell:" + miss.fdate,
                        opponent=[pretty(o) for o in miss.oppH], vtHome=miss.site == "H",
                        vtPoints=miss.vtPoints, oppPoints=miss.oppPoints, source="score only", pbp=False))
print("games with score only:", add[["date", "opponent", "vtPoints", "oppPoints"]].to_string(index=False))
g = pd.concat([g, add], ignore_index=True).sort_values("date").reset_index(drop=True)
g["site"] = [site.get(d, "H" if vh else "A") for d, vh in zip(g.date, g.vtHome)]
g.loc[(g.season == 2026), "site"] = np.where(g[g.season == 2026].vtHome, "H", "A")

# stat-crew game info: rank, attendance, weather, line scores
hs = pd.concat([pd.read_parquet(f) for f in glob.glob(D("hokiesports", "games", "*.parquet"))])
hs["gameId"] = hs.gameId.astype(str)
hs = hs.set_index("gameId")
kick = {}
for f in glob.glob(os.path.join(HERE, "hokiesports", "raw", "*.xml")):
    m = re.search(r'start="([^"]*)"', open(f, encoding="utf-8", errors="ignore").read(3000))
    if m:
        t = re.match(r"\s*(\d{1,2})[:.]?(\d{2})?\s*([apAP])?", m.group(1))
        if t and t.group(1):
            hr = int(t.group(1)) % 12 + (0 if (t.group(3) or "p").lower() == "a" else 12)
            if not t.group(3) and int(t.group(1)) in (10, 11): hr = int(t.group(1))
            kick[os.path.basename(f)[:-4]] = hr + int(t.group(2) or 0) / 60
wline = {}
for f in glob.glob(os.path.join(HERE, "hokiesports", "raw_wmt", "*.json")):
    j = json.load(open(f))["data"]; gid = os.path.basename(f)[:-5]
    t = pd.Timestamp(j["game_date"]); kick[gid] = t.hour + t.minute / 60
    for c in j["competitors"]:
        per = sorted((t_["period"], t_["statistic"].get("sPointsSG") or 0) for t_ in c["teamStats"] if t_["period"] and t_["period"] > 0)
        pts = [int(p) for _, p in per]
        if sum(pts) == c["score"]: wline[(gid, bool(c["homeContest"]))] = pts

es = pd.read_parquet(D("espn", "vt_schedule.parquet"))
et = pd.to_datetime(es.dateUTC, utc=True).dt.tz_convert("America/New_York")
es["date"] = et.dt.strftime("%Y-%m-%d"); es["koET"] = et.dt.hour + et.dt.minute / 60
es = es.set_index("date")
cf = pd.concat([pd.read_parquet(f) for f in glob.glob(D("games", "*.parquet"))])
cf = cf[cf.homePoints.notna()].set_index("id")

pen = pd.read_csv(D("derived", "penalties_by_game.csv")).set_index("date")
tk = pd.read_csv(D("derived", "vt_takeaways_by_game.csv")).set_index("date")

def lines(row):
    gid = row.hsGameId if isinstance(row.hsGameId, str) else None
    if gid and gid in hs.index and isinstance(hs.loc[gid].homeLine, str):
        x = hs.loc[gid]; hl, al = ([int(v) for v in s.split(",")] for s in (x.homeLine, x.awayLine))
        return (hl, al) if x.home == "Virginia Tech" else (al, hl)
    if gid and (gid, True) in wline and (gid, False) in wline:
        vt_home = hs.loc[gid].home == "Virginia Tech"
        return wline[(gid, vt_home)], wline[(gid, not vt_home)]
    if pd.notna(row.cfbdGameId) and row.cfbdGameId in cf.index:
        x = cf.loc[row.cfbdGameId]
        if x.homeLineScores is not None and len(x.homeLineScores):
            hl, al = [int(v) for v in x.homeLineScores], [int(v) for v in x.awayLineScores]
            return (hl, al) if x.homeTeam == "Virginia Tech" else (al, hl)
    return None, None

rows = []
for r in g.itertuples(index=False):
    gid = r.hsGameId if isinstance(r.hsGameId, str) else None
    x = hs.loc[gid] if gid and gid in hs.index else None
    e = es.loc[r.date] if r.date in es.index else None
    vr = orr = att = temp = None
    if x is not None:
        vth = x.home == "Virginia Tech"
        vr, orr = (x.homeRank, x.awayRank) if vth else (x.awayRank, x.homeRank)
        att, temp = x.attendance, x.get("temp")
    def num(v):
        m = None if v is None or pd.isna(v) else re.match(r"\s*(-?\d+)", str(v).replace(",", ""))
        return int(m.group(1)) if m and int(m.group(1)) != 0 else None
    vr, orr, att, temp = num(vr), num(orr), num(att), num(temp)
    if e is not None and r.season >= 2005:
        vr = vr if vr else num(e.vtRank); orr = orr if orr else num(e.oppRank)
    if e is not None and not att: att = num(e.attendance)
    if not att and pd.notna(r.cfbdGameId) and r.cfbdGameId in cf.index: att = num(cf.loc[r.cfbdGameId].attendance)
    ko = kick.get(gid) if gid else None
    if ko is None and e is not None: ko = float(e.koET)
    if ko is not None and ko < 9: ko = None
    vl, ol = lines(r)
    if vl and (sum(vl) != r.vtPoints or sum(ol) != r.oppPoints): vl = ol = None
    mth, day = int(r.date[5:7]), int(r.date[8:10])
    tag = None
    if r.date in ACCCG: tag = "ACC Championship"
    elif mth == 1 or (mth == 12 and day >= 14 and r.season != 2020):
        tag = BOWLS.get(r.season) or (e.note.title() if e is not None and isinstance(e.note, str) and e.note.strip() else "Bowl game")
        tag = re.sub(r"\s+(At|Presented By)\s.*$", "", tag).replace("'S", "'s").replace("Fedex", "FedEx").replace("Chick Fil-A", "Chick-fil-A").replace("Chick-Fil-A", "Chick-fil-A")
    p = pen.loc[r.date] if r.date in pen.index else None
    rows.append(dict(s=int(r.season), d=r.date, o=OPPNAME.get(r.opponent, r.opponent), site="N" if tag else SITEFIX.get(r.date, r.site),
                     vp=int(r.vtPoints), op=int(r.oppPoints), vr=vr, orr=orr, att=att, temp=temp,
                     ko=r1(ko, 2), tag=tag, pbp=bool(r.pbp), src=r.source, vl=vl, ol=ol, key=r.gameKey,
                     to=int(tk.loc[r.date].takeaways) if r.date in tk.index else None,
                     pen=None if p is None else dict(vt=[int(p.VT_pre_snap_n), int(p.VT_football_n), int(p.VT_discipline_n)],
                                                    opp=[int(p.opp_pre_snap_n), int(p.opp_football_n), int(p.opp_discipline_n)],
                                                    vy=int(p.VT_yds), oy=int(p.opp_yds))))
G = pd.DataFrame(rows)

# ---------------------------------------------------------------- plays
p = pd.concat([pd.read_parquet(f) for f in glob.glob(D("unified", "plays", "*.parquet"))])
need = p.distance * np.select([p.down == 1, p.down == 2], [0.5, 0.7], 1.0)
p["succ"] = (p.yards >= need) & (p.category != "int")
p["run"] = p.category == "rush"
p["expl"] = np.where(p.run, p.yards >= 12, p.yards >= 16)
p["sack"] = p.category == "sack"
p["to_"] = (p.category == "int")

def agg(d):
    return dict(n=int(len(d)), ypp=r1(d.yards.mean(), 2), sr=r1(100 * d.succ.mean()), ex=r1(100 * d.expl.mean()),
                run=r1(100 * d.run.mean()), sk=r1(100 * d.sack.sum() / max(1, (~d.run).sum())),
                ypc=r1(d[d.run].yards.mean(), 2), ypa=r1(d[~d.run].yards.mean(), 2))
bygame = {}
for (k, off), d in p.groupby(["gameKey", "vtOffense"]):
    bygame.setdefault(k, {})["off" if off else "def"] = agg(d)
G["off"] = [bygame.get(k, {}).get("off") for k in G.key]
G["def"] = [bygame.get(k, {}).get("def") for k in G.key]
G["nsr"] = [r1(a["sr"] - b["sr"]) if a and b else None for a, b in zip(G.off, G["def"])]

# ---------------------------------------------------------------- Elo-style rating from Howell scores
K, HFA, R = 35, 55, 0.2
hh = h.sort_values("fdate")
rating, last, vt_elo, snap = {}, None, {}, {}
for row in hh.itertuples(index=False):
    if row.season != last:
        if last is not None: snap[last] = dict(rating)
        for t in rating: rating[t] = 1500 + (rating[t] - 1500) * (1 - R)
        last = row.season
    a, b = row.team, row.opp
    ra = rating.setdefault(a, 1500.0); rb = 1200.0 if b == "NONIA" else rating.setdefault(b, 1500.0)
    edge = ra - rb + HFA * row.home
    e = 1 / (1 + 10 ** (-edge / 400)); m = row.pf - row.pa
    s = 1.0 if m > 0 else 0.0 if m < 0 else 0.5
    mov = math.log(abs(m) + 1) * 2.2 / (0.001 * (edge if m > 0 else -edge) + 2.2)
    dl = K * mov * (s - e)
    rating[a] = ra + dl
    if b != "NONIA": rating[b] = rb - dl
    if "VirginiaTech" in (a, b):
        isA = a == "VirginiaTech"
        vt_elo[row.fdate] = dict(pre=ra if isA else rb, post=rating["VirginiaTech"], wp=e if isA else 1 - e, opp=rb if isA else ra)
snap[last] = dict(rating)
# 2026: carry the 2025 close forward with the repo's ESPN-based Elo movement
start26 = 1500 + (snap[2025]["VirginiaTech"] - 1500) * (1 - R)
eg = pd.read_parquet(D("elo", "games.parquet")); eg = eg[(eg.season == 2026) & eg.completed & ((eg.homeTeam == "Virginia Tech") | (eg.awayTeam == "Virginia Tech"))].sort_values("date")
pre = [float(np.where(x.homeTeam == "Virginia Tech", x.homeElo, x.awayElo)) for x in eg.itertuples()]
wp = [float(x.homeWinProb if x.homeTeam == "Virginia Tech" else 1 - x.homeWinProb) for x in eg.itertuples()]
cur = pd.read_csv(D("elo", "ratings_current.csv")); now = float(cur[cur.team == "Virginia Tech"].elo.iloc[0])
seq = pre + [now]
d26 = sorted(d for d in G.d if d.startswith("2026"))
assert len(d26) == len(eg), (len(d26), len(eg))
for i, x in enumerate(eg.itertuples()):
    vt_elo[d26[i]] = dict(pre=start26 + seq[i] - seq[0], post=start26 + seq[i + 1] - seq[0], wp=wp[i], opp=None)
G["elo"] = [r1(vt_elo[d]["post"], 0) if d in vt_elo else None for d in G.d]
G["wp"] = [r1(100 * vt_elo[d]["wp"], 0) if d in vt_elo else None for d in G.d]
elo_rank = {}
for s, rt in snap.items():
    order = sorted(rt, key=rt.get, reverse=True)
    elo_rank[s] = (order.index("VirginiaTech") + 1, len(order), round(rt["VirginiaTech"]))
elo_rank[2026] = (int(cur[cur.team == "Virginia Tech"]["rank"].iloc[0]), None, round(start26 + now - seq[0]))

# ---------------------------------------------------------------- seasons
dfn = pd.read_csv(D("derived", "vt_defense_by_season.csv")).set_index("season")
ft = pd.read_csv(D("derived", "fbs_takeaways_by_season.csv")).set_index("season")
seasons = []
for s, d in G.groupby("s"):
    ps = p[p.season == s]
    w, l, t = int((d.vp > d.op).sum()), int((d.vp < d.op).sum()), int((d.vp == d.op).sum())
    pg = d[d.pen.notna()]
    penavg = lambda side: [r1(np.mean([x[side][i] for x in pg.pen]), 2) for i in range(3)] if len(pg) else None
    rk = d[d.orr.notna()]
    seasons.append(dict(s=int(s), coach=COACH(s), conf=CONF(s), w=w, l=l, t=t, n=len(d),
        pf=r1(d.vp.mean()), pa=r1(d.op.mean()),
        off=agg(ps[ps.vtOffense]) if len(ps) else None, deff=agg(ps[~ps.vtOffense]) if len(ps) else None,
        pbpGames=int(d.pbp.sum()),
        defRank=int(dfn.loc[s]["rank"]) if s in dfn.index and pd.notna(dfn.loc[s]["rank"]) else None,
        defOf=int(dfn.loc[s]["of"]) if s in dfn.index and pd.notna(dfn.loc[s]["of"]) else None,
        defPct=r1(dfn.loc[s].pct) if s in dfn.index else None,
        tpg=r1(d.to.dropna().mean(), 2) if d.to.notna().any() else None,
        fbsT=r1(ft.loc[s].fbsAvg, 2) if s in ft.index else None,
        elo=elo_rank.get(s, (None, None, None))[2], eloRank=elo_rank.get(s, (None,))[0], eloOf=elo_rank.get(s, (None, None))[1],
        night=int((d.ko >= 18).sum()), koN=int(d.ko.notna().sum()),
        penVT=penavg("vt"), penOpp=penavg("opp"),
        penYdsVT=r1(np.mean([x["vy"] for x in pg.pen])) if len(pg) else None,
        penYdsOpp=r1(np.mean([x["oy"] for x in pg.pen])) if len(pg) else None,
        rkW=int((rk.vp > rk.op).sum()), rkL=int((rk.vp < rk.op).sum()),
        hiRank=int(d.vr.min()) if d.vr.notna().any() else None,
        homeAtt=r1(d[(d.site == "H") & d.att.notna()].att.mean(), 0) if d[(d.site == "H")].att.notna().any() else None))

# ---------------------------------------------------------------- play-level cuts
ERAS = [("All seasons", 1987, 2026), ("1987-1994", 1987, 1994), ("1995-2004", 1995, 2004),
        ("2005-2011", 2005, 2011), ("2012-2019", 2012, 2019), ("2020-2026", 2020, 2026)]
DB = [(1, 3, "1-3"), (4, 6, "4-6"), (7, 9, "7-9"), (10, 10, "10"), (11, 99, "11+")]
p["db"] = np.select([(p.distance >= a) & (p.distance <= b) for a, b, _ in DB], range(len(DB)))
p["fz"] = np.clip((p.yardsToGoal - 1) // 10, 0, 9)
dd, fz = {}, {}
for name, a, b in ERAS:
    e = p[(p.season >= a) & (p.season <= b)]
    for side, flag in (("off", True), ("def", False)):
        x = e[e.vtOffense == flag]
        cells = x.groupby(["down", "db"]).agg(n=("succ", "size"), sr=("succ", "mean"), run=("run", "mean"), y=("yards", "mean")).reset_index()
        dd[f"{name}|{side}"] = [[int(c.down), int(c.db), int(c.n), r1(100 * c.sr), r1(100 * c.run), r1(c.y, 1)] for c in cells.itertuples()]
        z = x.groupby("fz").agg(n=("succ", "size"), sr=("succ", "mean"), y=("yards", "mean"), ex=("expl", "mean")).reset_index()
        fz[f"{name}|{side}"] = [[int(c.fz), int(c.n), r1(100 * c.sr), r1(c.y, 2), r1(100 * c.ex)] for c in z.itertuples()]
# third downs by season
td = p[p.down == 3].groupby(["season", "vtOffense"]).agg(n=("succ", "size"), c=("succ", "mean"), dist=("distance", "mean")).reset_index()
third = [[int(x.season), bool(x.vtOffense), int(x.n), r1(100 * x.c), r1(x.dist, 1)] for x in td.itertuples()]
# longest VT offensive and allowed plays
def longest(d, k=12):
    d = d[(d.yards <= 99) & (d.yards + 0 <= d.yardsToGoal + 0)].sort_values("yards", ascending=False).head(k)
    return [dict(s=int(x.season), d=x.date, o=x.opponent, y=int(x.yards), c=x.category, t=re.sub(r"\s+", " ", x.text)[:150]) for x in d.itertuples()]
long_off, long_def = longest(p[p.vtOffense]), longest(p[~p.vtOffense])

# quarter scoring by coach era (regulation quarters only)
q = G[G.vl.notna()]
quarters = []
for c, d in q.groupby(q.s.map(COACH), sort=False):
    v = np.array([x[:4] for x in d.vl if len(x) >= 4]); o = np.array([x[:4] for x in d.ol if len(x) >= 4])
    quarters.append(dict(coach=c, n=len(v), vt=[r1(x, 2) for x in v.mean(0)], opp=[r1(x, 2) for x in o.mean(0)]))

# opponents
opps = []
for o, d in G.groupby("o"):
    if o == "Non-I-A opponent": continue
    opps.append(dict(o=o, n=len(d), w=int((d.vp > d.op).sum()), l=int((d.vp < d.op).sum()), t=int((d.vp == d.op).sum()),
                     mg=r1((d.vp - d.op).mean()), first=int(d.s.min()), last=int(d.s.max())))
opps.sort(key=lambda x: -x["n"])

G = G.drop(columns=["key"])
games = json.loads(G.to_json(orient="records"))
for x in games:
    for k in [k for k, v in x.items() if v is None]: del x[k]
site_json = dict(built=pd.Timestamp.now().strftime("%Y-%m-%d"), games=games, seasons=seasons, dd=dd, fz=fz, third=third,
                 distBuckets=[x[2] for x in DB], eras=[e[0] for e in ERAS], longOff=long_off, longDef=long_def,
                 quarters=quarters, opps=opps)
with open(os.path.join(OUT, "site.json"), "w") as f:
    json.dump(site_json, f, separators=(",", ":"))
print("games", len(games), "bytes", os.path.getsize(os.path.join(OUT, "site.json")))
