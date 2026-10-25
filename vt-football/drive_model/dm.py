"""Shared helpers for the multi-season drive model.

drives_from_summary() is the drive parser from drives.py (2026), unchanged in its rules, so every
season is cut the same way. venue_from_summary() pulls the venue/kickoff fields venues.py needs,
so the raw ESPN JSON can be deleted as soon as a game is parsed.
"""
import json, time, urllib.request
import numpy as np, pandas as pd

SUM = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={}"
UA = "vt-football-archive/1.0 (personal research; github.com/justinmorg)"
SEASONS = list(range(2016, 2027))


def fetch(eid, tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(SUM.format(eid), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if k == tries - 1: raise
            time.sleep(2 + 2 * k)


def games(season):
    g = pd.read_parquet(f"../data/espn/games/{season}.parquet")
    return g[g.completed].set_index("eventId")


def fbs_teams(g):
    return set(g.homeTeam[g.homeFBS]) | set(g.awayTeam[g.awayFBS])


def secs(c):
    try: m, s = c.split(":"); return int(m) * 60 + int(s)
    except Exception: return None


SKIP = ("Kickoff", "Timeout", "End Period", "Coin Toss", "End of")


def scoring_points(s):
    """{play id: (scoring team id, points)} from ESPN's scoringPlays, whose running scores are
    reliable (the per-play scores inside drives carry stale values on some plays, 2021-25
    especially). None if the list is missing or doesn't line up with the drive plays."""
    sp = s.get("scoringPlays") or []
    ids = {p.get("id") for d in (s.get("drives") or {}).get("previous", []) for p in d.get("plays", [])}
    if not sp or not all(p.get("id") in ids for p in sp): return None
    out, h0, a0 = {}, 0, 0
    for p in sp:
        h, a = p.get("homeScore", h0), p.get("awayScore", a0)
        out[p["id"]] = ((p.get("team") or {}).get("id"), max(h - h0, 0) + max(a - a0, 0))
        h0, a0 = max(h, h0), max(a, a0)
    return out


def drives_from_summary(s, g):
    """One row per drive. Start = first scrimmage snap's yardsToEndzone (kickoffs skipped);
    points = offense's points on the drive's scoring plays (spts=1), or, when ESPN's scoring-play
    list is unusable, the rise in the offense's own score over the drive (spts=0)."""
    comp = s["header"]["competitions"][0]; eid = int(comp["id"])
    team = {c["id"]: c["team"]["location"] for c in comp["competitors"]}
    hid = next(c["id"] for c in comp["competitors"] if c["homeAway"] == "home")
    neutral = bool(g.loc[eid, "neutralSite"])
    prev = (0, 0); rows = []
    sp_pts = scoring_points(s)
    for d in (s.get("drives") or {}).get("previous", []):
        pl = d.get("plays", [])
        if not pl: continue
        if not (d.get("team") or any(p.get("teamParticipants") for p in pl)): continue
        tid = (d.get("team") or {}).get("id") or next(
            (x["id"] for p in pl for x in p.get("teamParticipants", []) if x.get("type") == "offense"), None)
        off = team.get(tid); dfn = next((v for k, v in team.items() if k != tid), None)
        scr = [p for p in pl if (p.get("start") or {}).get("down")
               and not any(k in (p.get("type") or {}).get("text", "") for k in SKIP)]
        ytg = scr[0]["start"].get("yardsToEndzone") if scr else None
        if sp_pts is not None:
            # points credited to this drive's offense by ESPN's scoring-play list (clean running
            # totals); defensive/return scores and safeties go to the other team, so they drop out
            pts = sum(sp_pts.get(p.get("id"), (None, 0))[1] for p in pl
                      if sp_pts.get(p.get("id"), (None, 0))[0] == tid)
        else:  # no usable scoring-play list: 2026's original rule (score change over the drive)
            end = (pl[-1].get("homeScore", prev[0]), pl[-1].get("awayScore", prev[1]))
            ishome = tid == hid
            pts = (end[0] - prev[0]) if ishome else (end[1] - prev[1])
            prev = end
        q = (d.get("start") or {}).get("period", {}).get("number") or pl[0]["period"]["number"]
        clk = secs(((d.get("start") or {}).get("clock") or pl[0].get("clock") or {}).get("displayValue"))
        rows.append(dict(eid=eid, date=g.loc[eid, "date"], off=off, dfn=dfn,
                         home=0 if neutral else (1 if tid == hid else -1), q=q, clock=clk, ytg=ytg,
                         pts=max(pts, 0), result=d.get("result"), plays=d.get("offensivePlays"),
                         spts=int(sp_pts is not None)))
    return rows


def venue_from_summary(s):
    c = s["header"]["competitions"][0]; v = (s.get("gameInfo") or {}).get("venue") or {}
    a = v.get("address") or {}
    return dict(eid=int(c["id"]), kick=c["date"], venue=v.get("id"), vname=v.get("fullName"),
                city=a.get("city"), state=a.get("state"), country=a.get("country"))


def clean(D, fbs):
    """Points: from the scoring-play list a drive's offense points are kept as 3 or 6-8 (anything
    else is 0); without it, ep.py's rule (TD drives 6-8, FG drives 3). Valid starts only; FCS pooled."""
    import numpy as np
    D = D.copy()
    sp = D.get("spts", pd.Series(0, index=D.index)).fillna(0).astype(bool)
    old = np.where(D.result == "TD", np.where(D.pts >= 6, D.pts.clip(upper=8), 0),
                   np.where((D.result == "FG") & (D.pts == 3), 3, 0))
    new = np.where(D.pts.isin([3, 6, 7, 8]), D.pts, 0)
    D["pts"] = np.where(sp, new, old).astype(float)
    D = D[D.ytg.notna() & D.ytg.between(1, 99)].copy()
    D["offT"] = D.off.where(D.off.isin(fbs), "FCS"); D["dfnT"] = D.dfn.where(D.dfn.isin(fbs), "FCS")
    D["late"] = (D.q.isin([2, 4]) & (D.clock <= 60)) | (D.q > 4)
    return D


def ep_curve(fit):
    """ep3.py's curve: isotonic in yards to go, smoothed (3 yd), mean-preserving. fit: drives."""
    from sklearn.isotonic import IsotonicRegression
    iso = IsotonicRegression(increasing=False, out_of_bounds='clip').fit(fit.ytg.astype(float), fit.pts)
    grid = np.arange(1, 100); f = iso.predict(grid)
    sm = np.array([np.average(f, weights=np.exp(-0.5 * ((grid - g0) / 3) ** 2)) for g0 in grid])
    sm = np.minimum.accumulate(sm)                       # keep it non-increasing after smoothing
    sm += fit.pts.mean() - pd.Series(sm, grid)[fit.ytg.round().clip(1, 99).astype(int)].mean()  # keep the mean
    return pd.Series(sm, index=grid)


def ratings(A, y, lam=40):
    """Ridge offense + defense + home field (vtdef.py). Returns (team table, home, fitted)."""
    teams = sorted(set(A.offT) | set(A.dfnT)); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    M = np.zeros((len(A), 2 * n + 1))
    M[np.arange(len(A)), A.offT.map(ix).values] = 1; M[np.arange(len(A)), n + A.dfnT.map(ix).values] = 1
    M[:, 2 * n] = A.home.values
    c = np.linalg.solve(M.T @ M + lam * np.diag(np.r_[np.ones(2 * n), 0]), M.T @ y)
    return pd.DataFrame(dict(team=teams, off=c[:n], dfn=c[n:2 * n])), c[2 * n], M @ c
