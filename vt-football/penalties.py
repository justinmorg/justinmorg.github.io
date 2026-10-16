"""VT penalty profile in three buckets: pre-snap, football (live-ball technique), discipline.

Buckets (classified by penalty type; edge cases are not hand-checked):
  pre_snap    mental / alignment errors before the snap: false start, illegal formation,
              illegal procedure, illegal shift, illegal motion, illegal substitution, too many
              men, delay of game, offside, encroachment, neutral zone infraction.
  football    live-ball fouls that come from blocking, covering, rushing, tackling: holding,
              pass interference, illegal block / clipping / chop block, illegal use of hands,
              illegal contact, tripping, ineligible downfield, FACE MASK, intentional grounding,
              kick-catch interference, running into the kicker.
  discipline  loss of control: unsportsmanlike conduct, taunting, celebration, unnecessary
              roughness, generic "personal foul", ROUGHING THE PASSER, roughing the kicker,
              late hit, horse collar, targeting, fighting, sideline interference.
  other       anything the patterns don't recognize (shown so it can be added).

Sources, following the unified table's choice per game (data/unified/games.parquet):
  hokiesports XML  structured <penalty vh type result yards> per play (1987-2019 games)
  hokiesports WMT  play text, "PENALTY <team> <type> (player) N yards" (2026 Pitt, California)
  cfbd             play text in three formats (old "X penalty 5 yard type accepted", newer
                   "X Penalty, type (player) (N Yards)", and StatCrew-style "PENALTY X ...");
                   penalty yards are missing from a share of the newer CFBD text.
  statcrew_text    2004 Sugar Bowl only; skipped (no penalty parsing yet)

Only accepted penalties are counted; declined and offsetting are kept in the play-level file.

Outputs:
  data/derived/penalties_by_play.csv   one row per penalty
  data/derived/penalties_by_game.csv   per game, VT and opponent count / yards by bucket, plus
                                       official totals where known (XML <totals>, WMT box,
                                       ESPN box for CFBD games: data/espn/penalties/)
Usage:  python penalties.py [--espn]    (--espn re-pulls ESPN penalty totals for CFBD games)
"""
import glob, json, os, re, sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")

RULES = [  # first match wins; order matters (running into before roughing, etc.)
    ("football", r"running into"),
    ("discipline", r"unsportsman|\bUNS\b|taunt|celebrat|unnecessary rough|\bUNR\b|personal foul|"
                   r"roughing|late hit|horse ?collar|targeting|fight|spear|sideline|disqualif"),
    ("pre_snap", r"false start|illegal formation|illegal procedure|illegal shift|illegal motion|"
                 r"substitution|12 men|too many|delay of game|offside|encroach|neutral zone|"
                 r"illegal snap|disconcert|illegal participation|illegal formatn|snap infraction"),
    ("football", r"hold|interference|illegal block|block in.*back|clipping|chop|block below|"
                 r"use of hands|illegal contact|trip|ineligible|face ?mask|grounding|"
                 r"illegal forward|illegal pass|illegal touch|illegal bat|fair catch|kick.*out of bounds|"
                 r"out of bounds.*kick|illegal kick|illegal wedge|helping|illegal return|"
                 r"illegal crack|hands to the face|illegal blindside|illegal screen|player out of bounds"),
]
VT_ALIASES = r"(?:virginia tech|vt|vtech|vatech|va tech|hokies|v tech)"


def bucket(t):
    t = (t or "").lower()
    for b, pat in RULES:
        if re.search(pat, t, re.I):
            return b
    return "other"


def clean_type(t):
    t = re.sub(r"\s+", " ", t or "").strip(" ,.-")
    return t.lower()


# ---------- text parsers (CFBD + WMT) ----------
CODES = {"hd": "holding", "hold": "holding", "oh": "holding", "h": "holding", "h0": "holding",
         "dh": "holding", "if": "illegal formation", "off": "offside", "of": "offside", "0f": "offside",
         "0s": "offside", "os": "offside", "bib": "illegal block in the back", "ib": "illegal block",
         "ip": "illegal procedure", "im": "illegal motion", "fs": "false start", "targ": "targeting",
         "pf": "personal foul", "pi": "pass interference", "dpi": "pass interference",
         "opi": "pass interference", "uns": "unsportsmanlike conduct", "unr": "unnecessary roughness",
         "dog": "delay of game", "ids": "ineligible downfield"}
# StatCrew / WMT style, upper-case PENALTY (case-sensitive on purpose: lower-case "penalty" is the
# old CFBD format). One segment = team code, type, optional (player), optional "on X",
# optional "enforced", optional N yards, optional declined/offsetting.
SEG = re.compile(
    r"\s*(?:Before the snap,\s*)?([A-Za-z][A-Za-z&.'\-]*)\s+"
    r"([^(,.;]+?)"
    r"(?=\s*\(|\s+on\s+[A-Z#]|\s+enforced|\s+-?\d+\s+yards?\b|\s+declined|\s+offsetting|\s*[,.;]|$)"
    r"(?:\s*\([^)]*\))?(?:\s+on\s+[^0-9.]+?(?=\s+enforced|\s+-?\d+\s+yards?|\s+declined))?"
    r"(?:\s+enforced)?(?:\s+(-?\d+)\s+yards?\b)?(?:[^.]{0,40}?\b(declined|offsetting))?")
NEW = re.compile(  # VIRGINIA TECH Penalty, False Start (Player) (5 Yards) to the ...
    r"([A-Za-z&.'() ]{2,40}?)\s+Penalty,\s*(.*?)(?=\s*\(|\s+to the|\s+declined|\s+offsetting|$)"
    r"((?:\s*\([^)]*\))*)\s*(declined|offsetting)?", re.I)
OLD = re.compile(  # VIRGINIA TECH penalty 5 yard False Start on X accepted / declined
    r"([A-Za-z&.'() ]{2,40}?)\s+penalty\s+(?:(-?\d+)\s+yards?\s+)?([^,]*?)(?:\s+on\s+[^,]+?)?\s*(accepted|declined|offsetting|(?=,)|$)",
    re.I)


def is_vt(team):
    t = re.sub(r"\s+", " ", team.strip().lower())
    return bool(re.search(r"(?:^|\s)" + VT_ALIASES + r"$", t)) or t in ("va", "vpi", "vat", "vtu")


def norm_type(t):
    t = re.sub(r"^\s*(?:uns|unr|pf):\s*", "", t or "", flags=re.I)
    t = clean_type(re.sub(r"\s+on\s+.*$|\s+/\s+(?:offense|defense).*$", "", t, flags=re.I))
    return CODES.get(t, t) or "unknown"


def res_of(r):
    r = (r or "accepted").lower()
    return "DECLINE" if r.startswith("decl") else "OFFSET" if r.startswith("offs") else "ACCEPT"


def parse_text(text):
    """Return list of (isVT, type, result, yards) found in one play's text."""
    out, s = [], text if isinstance(text, str) else ""
    # replay reviews repeat the original play text; only the ruling on the field after review counts
    s = re.sub(r"\(Original Play:.*$", "", s)
    # some 2025 WMT feeds glue the team code to the foul: "PENALTY VTFalse Start"
    s = re.sub(r"PENALTY ([A-Z]{2,5}?)(UNS:|UNR:|[A-Z][a-z])", r"PENALTY \1 \2", s)
    # 2021 MTSU-style feed: "PENALTY on MTS-G.Grate, Unnecessary Roughness / Defense, 15 yards, offset."
    for m in re.finditer(r"PENALTY on ([A-Za-z]+)-[^,]*,\s*([^,]+?),\s*(?:(-?\d+) yards?,\s*)?(accepted|declined|offset)", s, re.I):
        team, typ, yds, res = m.groups()
        res = res_of(res)
        out.append((is_vt(team), norm_type(typ), res, abs(int(yds)) if yds and res == "ACCEPT" else None))
    if out:
        return out
    for m in re.finditer(r"PENALTY\b(?! on )", s):
        pos, segs = m.end(), []
        while True:
            sm = SEG.match(s, pos)
            if not sm or not sm.group(2).strip():
                break
            team, typ, yds, res = sm.groups()
            # a continuation must be another foul ("... Offside (X) VMI UNR: ... 20 yards"), not "from VT30 to ..."
            if segs and (team.lower() in ("from", "to", "no", "and") or bucket(norm_type(typ)) == "other"):
                break
            segs.append([is_vt(team), norm_type(typ), res_of(res), abs(int(yds)) if yds else None])
            pos = sm.end()
        # two fouls written as one enforcement: give a yardless pre-snap foul its 5 and the rest to the other
        if len(segs) == 2 and segs[0][3] is None and segs[1][3] and bucket(segs[0][1]) == "pre_snap" \
                and segs[0][2] == segs[1][2] == "ACCEPT" and segs[1][3] > 5:
            segs[0][3], segs[1][3] = 5, segs[1][3] - 5
        for isvt, typ, res, yds in segs:
            out.append((isvt, typ, res, yds if res == "ACCEPT" else None))
    if out:
        return out
    old = [m.groups() for m in OLD.finditer(s) if m.group(4) or "offsetting" in s[m.end():]]
    for team, yds, typ, res in old:
        res = res_of(res or "offsetting")
        out.append((is_vt(team), norm_type(typ), res, abs(int(yds)) if yds and res == "ACCEPT" else None))
    if out:
        return out
    for m in NEW.finditer(s):
        team, typ, parens, res = m.groups()
        ym = re.search(r"\((-?\d+)\s*yards?\)", parens or "", re.I)
        res = res_of(res)
        out.append((is_vt(team), norm_type(typ), res, abs(int(ym.group(1))) if ym and res == "ACCEPT" else None))
    if out:
        return out
    for m in re.finditer(r"(\d+) yard penalty on ([A-Za-z .'&]+)", s):  # 2001 CFBD, no type given
        out.append((is_vt(m.group(2)), "unknown", "ACCEPT", int(m.group(1))))
    return out


# ---------- per-source extraction ----------
def from_xml(g):
    gid = int(g.hsGameId)
    p = pd.read_parquet(os.path.join(D, "hokiesports", "plays", f"{gid}.parquet"))
    hg = pd.read_parquet(os.path.join(D, "hokiesports", "games", f"{gid}.parquet")).iloc[0]
    vt_vh = "H" if hg.home == "Virginia Tech" else "V"
    rows = []
    for r in p[p.penalties.notna()].itertuples():
        for item in r.penalties.split(";"):
            parts = item.split(":")
            if len(parts) < 4:
                continue
            vh, typ, res, yds = parts[0], parts[1], parts[2], parts[3]
            rows.append(dict(isVT=(vh == vt_vh), type=norm_type(typ), result=res.upper()[:6],
                             yards=int(yds) if yds.lstrip("-").isdigit() and res.upper() == "ACCEPT" else None,
                             quarter=r.quarter, text=r.text))
    # official totals
    off = {}
    raw = os.path.join(HERE, "hokiesports", "raw", f"{gid}.xml")
    if os.path.exists(raw):
        root = ET.parse(raw).getroot()
        for t in root.findall("team"):
            pn = t.find("totals/penalties")
            if pn is not None:
                off["VT" if t.get("vh") == vt_vh else "opp"] = (int(pn.get("no") or 0), int(pn.get("yds") or 0))
    elif os.path.exists(os.path.join(HERE, "hokiesports", "raw_wmt", f"{gid}.json")):
        return from_wmt(g, p)
    return rows, off


def from_wmt(g, p):
    gid = int(g.hsGameId)
    rows = []
    for r in p.itertuples():
        for isvt, typ, res, yds in parse_text(r.text):
            rows.append(dict(isVT=isvt, type=typ, result=res, yards=yds, quarter=r.quarter, text=r.text))
    # dead-ball penalties keyed without a clock live only in the raw JSON's play list
    d = json.load(open(os.path.join(HERE, "hokiesports", "raw_wmt", f"{gid}.json")))["data"]
    have = set(p.text.dropna())

    def strings(o):
        if isinstance(o, dict):
            for v in o.values(): yield from strings(v)
        elif isinstance(o, list):
            for v in o: yield from strings(v)
        elif isinstance(o, str):
            yield o
    for pl in strings(d):
        if "PENALTY" in pl and pl not in have and len(pl) < 600:
            have.add(pl)
            for isvt, typ, res, yds in parse_text(pl):
                rows.append(dict(isVT=isvt, type=typ, result=res, yards=yds, quarter=None, text=pl))
    off = {}
    for c in d["competitors"]:
        st = {}
        for ts in c.get("teamStats", []):
            if isinstance(ts.get("statistic"), dict):
                st.update(ts["statistic"])
        vt = st.get("cTeamPointsScored", st.get("sPointsSG")) == g.vtPoints
        if "sPenalties" in st:
            off["VT" if vt else "opp"] = (int(st["sPenalties"]), int(st.get("sPenaltyYards") or 0))
    return rows, off


def from_cfbd(g, plays):
    p = plays[plays.gameId == int(g.cfbdGameId)]
    rows = []
    for r in p.itertuples():
        for isvt, typ, res, yds in parse_text(r.playText):
            if yds is None and res == "ACCEPT" and r.playType == "Penalty" and pd.notna(r.yardsGained):
                yds = abs(int(r.yardsGained)) or None
            rows.append(dict(isVT=isvt, type=typ, result=res, yards=yds, quarter=r.period, text=r.playText))
    return rows, {}


# ---------- ESPN official totals for CFBD games ----------
ESPN_SUM = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={id}"


def espn_pen(eid):
    from espn import get
    try:
        d = get(ESPN_SUM.format(id=eid))
    except Exception:
        return eid, None
    out = {}
    for t in d.get("boxscore", {}).get("teams", []):
        st = {s["name"]: s.get("displayValue") for s in t.get("statistics", [])}
        v = st.get("totalPenaltiesYards")
        if v and "-" in v:
            n, y = v.split("-", 1)
            out["VT" if t["team"].get("abbreviation") == "VT" else "opp"] = (int(n), int(y))
    return eid, out or None


def espn_totals(games, refresh):
    path = os.path.join(D, "espn", "penalties", "vt_games.parquet")
    if os.path.exists(path) and not refresh:
        e = pd.read_parquet(path)
    else:
        ids = games.cfbdGameId.dropna().astype(int).tolist()
        with ThreadPoolExecutor(8) as ex:
            res = dict(ex.map(espn_pen, ids))
        e = pd.DataFrame([dict(cfbdGameId=k, vtN=v["VT"][0], vtY=v["VT"][1], oppN=v["opp"][0], oppY=v["opp"][1])
                          for k, v in res.items() if v and "VT" in v and "opp" in v and v["VT"] + v["opp"] != (0, 0, 0, 0)])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        e.to_parquet(path, index=False)
    return {int(r.cfbdGameId): {"VT": (r.vtN, r.vtY), "opp": (r.oppN, r.oppY)} for r in e.itertuples()}


def main():
    games = pd.read_parquet(os.path.join(D, "unified", "games.parquet"))
    plays = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(D, "plays", "*.parquet")))],
                      ignore_index=True)
    espn = espn_totals(games[games.source == "cfbd"], "--espn" in sys.argv)
    pen_rows, game_rows = [], []
    for g in games.sort_values(["season", "date"]).itertuples():
        if g.source == "hokiesports":
            rows, off = from_xml(g)
        elif g.source == "cfbd":
            rows, off = from_cfbd(g, plays)
            off = espn.get(int(g.cfbdGameId), {})
        else:
            continue
        for r in rows:
            r.update(season=g.season, date=g.date, opponent=g.opponent, source=g.source,
                     team="VT" if r["isVT"] else "opp", bucket=bucket(r["type"]))
            pen_rows.append(r)
        df = pd.DataFrame(rows)
        rec = dict(season=g.season, date=g.date, opponent=g.opponent, vtHome=g.vtHome,
                   vtPoints=g.vtPoints, oppPoints=g.oppPoints, source=g.source)
        for side in ("VT", "opp"):
            a = df[(df.isVT == (side == "VT")) & (df.result == "ACCEPT")] if len(df) else df
            rec[f"{side}_n"] = len(a)
            rec[f"{side}_yds"] = int(a.yards.fillna(0).sum()) if len(a) else 0
            rec[f"{side}_ydsMissing"] = int(a.yards.isna().sum()) if len(a) else 0
            for b in ("pre_snap", "football", "discipline", "other"):
                s = a[a.type.map(bucket) == b] if len(a) else a
                rec[f"{side}_{b}_n"] = len(s)
                rec[f"{side}_{b}_yds"] = int(s.yards.fillna(0).sum()) if len(s) else 0
            n, y = off.get(side, (None, None))
            rec[f"{side}_official_n"], rec[f"{side}_official_yds"] = n, y
        game_rows.append(rec)
    out = os.path.join(D, "derived")
    pd.DataFrame(pen_rows)[["season", "date", "opponent", "source", "team", "quarter", "type", "bucket",
                            "result", "yards", "text"]].to_csv(os.path.join(out, "penalties_by_play.csv"), index=False)
    gdf = pd.DataFrame(game_rows)
    gdf.to_csv(os.path.join(out, "penalties_by_game.csv"), index=False)
    chk = gdf.dropna(subset=["VT_official_n"])
    for side in ("VT", "opp"):
        ok = (chk[f"{side}_n"] == chk[f"{side}_official_n"]).mean()
        print(f"{side}: count matches official in {ok:.0%} of {len(chk)} games")
    print(len(gdf), "games,", len(pen_rows), "penalty rows")


if __name__ == "__main__":
    main()
