#!/usr/bin/env python3
"""Thread 9, step 3b: turn the private extract into per-player-month PGNs
that are safe to commit.

    python3 panel_anon.py /home/claude/panel [--pairs 120]

Reads  <dir>/extract_2025-09.pgn.gz, extract_2026-09.pgn.gz (panel_extract.sh)
       <dir>/panel_ranks_private.csv, <dir>/panel_secret.txt (panel_select.py)
Writes <dir>/pm/<id>_<yymm>.pgn   one file per player-month, ready for annot_inc
       <dir>/pm/manifest.csv      id, month, games available, games kept
       <dir>/gid_map_private.csv  hashed GameId -> real Lichess game id (PRIVATE)

Per panel_prespec.md: a player-month over 250 games is sampled down to 250 at
random, seeded per player-month from seed 23, then put back in time order.

Anonymisation: every panel player's name becomes their id, every other name
becomes OPP, Site is blanked, and a GameId tag is added as a keyed hash of the
real game id (annot_inc.py resumes by GameId). Ratings, dates, clocks and
moves are kept -- the analysis needs them -- so a determined reader with the
public database could still match games. The repo holds no usernames; it is
not a promise that the games cannot be traced.
"""
import csv, gzip, hmac, hashlib, os, random, re, sys
from collections import defaultdict

CAP = 250
TAG = re.compile(r'^\[(\w+) "(.*)"\]$', re.M)

def games(path):
    """Yield (header, movetext) pairs from the extract's paragraph format."""
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        buf, hdr = [], None
        for block in f.read().split("\n\n"):
            block = block.strip("\n")
            if not block: continue
            if block.startswith("[Event "):
                hdr = block
            elif hdr is not None:
                yield hdr, block; hdr = None

def main(d, pairs):
    key = bytes.fromhex(open(os.path.join(d, "panel_secret.txt")).read().strip())
    def h(s): return hmac.new(key, s.encode(), hashlib.sha256).hexdigest()[:10]
    rows = [r for r in csv.DictReader(open(os.path.join(d, "panel_ranks_private.csv")))
            if int(r["pair"]) <= pairs]
    pid = {r["username"].lower(): r["id"] for r in rows}
    out = os.path.join(d, "pm"); os.makedirs(out, exist_ok=True)
    gmap = open(os.path.join(d, "gid_map_private.csv"), "w", newline="")
    gw = csv.writer(gmap); gw.writerow(["GameId", "lichess_id"])
    man = []
    for month, yymm in (("2025-09", "2509"), ("2026-09", "2609")):
        per = defaultdict(list)
        for hdr, mv in games(os.path.join(d, f"extract_{month}.pgn.gz")):
            t = dict(TAG.findall(hdr))
            real = t["Site"].rsplit("/", 1)[-1]
            g = "g" + h("game:" + real)
            gw.writerow([g, real])
            w, b = t["White"].lower(), t["Black"].lower()
            def anon(line):
                m = TAG.match(line)
                if not m: return line
                k, v = m.groups()
                if k in ("White", "Black"):
                    return f'[{k} "{pid.get(v.lower(), "OPP")}"]'
                if k == "Site": return '[Site "?"]\n[GameId "%s"]' % g
                return line
            text = "\n".join(anon(l) for l in hdr.split("\n")) + "\n\n" + mv + "\n"
            key_t = (t.get("UTCDate", ""), t.get("UTCTime", ""), g)
            for u in (w, b):
                if u in pid: per[pid[u]].append((key_t, text))
        for r in rows:
            p = r["id"]; gl = per.get(p, [])
            avail = len(gl)
            if avail > CAP:
                gl = random.Random(f"23-{p}-{yymm}").sample(gl, CAP)
            gl.sort(key=lambda x: x[0])
            with open(os.path.join(out, f"{p}_{yymm}.pgn"), "w") as f:
                f.write("\n".join(t for _, t in gl))
            man.append([p, r["pair"], r["group"], yymm, avail, len(gl)])
    gmap.close()
    with open(os.path.join(out, "manifest.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "pair", "group", "month", "available", "kept"])
        w.writerows(man)
    short = [m for m in man if m[5] < 150]
    print(f"player-months written: {len(man)}; under 150 games: {len(short)}")
    for m in short[:20]: print("  short:", m)

if __name__ == "__main__":
    a = sys.argv[1:]
    pairs = int(a[a.index("--pairs") + 1]) if "--pairs" in a else 120
    main(a[0] if a and not a[0].startswith("--") else "/home/claude/panel", pairs)
