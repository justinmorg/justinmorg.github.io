#!/usr/bin/env python3
"""Thread 9, step 2: select the improvers-vs-controls panel.

Implements "Panel selection" in panel_prespec.md exactly; read that, not this,
for the reasons. Uses only ratings, game counts and account flags -- no error
rate exists yet when this runs.

    python3 panel_select.py /home/claude/panel

Reads  <dir>/index_2025-09.tsv.gz, <dir>/index_2026-09.tsv.gz (panel_index.sh)
Writes, all in <dir> (PRIVATE -- real usernames or re-identifying detail):
    panel_secret.txt   32-byte HMAC secret (hex). Give to Justin; never commit.
    panel_key.csv      id,username for every ranked player. Give to Justin.
    panel_ranks_private.csv  full selection table, usernames included
    panel_ranks.csv    rank,pair,group,id only -- the one file safe to commit
    panel_select.log   counts at every stage
The secret is reused if panel_secret.txt already exists, so ids are stable.
"""
import csv, gzip, hmac, hashlib, json, os, random, secrets, sys, time
import urllib.request
from collections import defaultdict

SEED = 23
TCS = {"180+2", "300+0"}
BAD_TERM = {"Abandoned", "Rules infraction"}
EXCLUDE = {"jamorgan"}             # group F treatment block: never read
MIN_N, LO, HI = 150, 1150, 1750
IMP_MIN, IMP_MAX, CTRL_ABS = 150, 300, 50
PERSIST = 100
MATCH_ELO, MATCH_NRATIO = 30, 2.0

def month_stats(path):
    n = defaultdict(int); s = defaultdict(int); kept = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 13: continue
            gid, dt, tm, wh, bl, we, be, wd, bd, res, tc, arena, term = p[:13]
            if arena != "0" or tc not in TCS or term in BAD_TERM: continue
            try: we, be = int(we), int(be)
            except ValueError: continue
            kept += 1
            for u, r in ((wh.lower(), we), (bl.lower(), be)):
                n[u] += 1; s[u] += r
    return {u: (n[u], s[u] / n[u]) for u in n}, kept

def api_users(names, log):
    out = {}
    names = sorted(names)
    for i in range(0, len(names), 300):
        chunk = names[i:i + 300]
        for attempt in range(5):
            try:
                req = urllib.request.Request("https://lichess.org/api/users",
                    data=",".join(chunk).encode(), method="POST",
                    headers={"Content-Type": "text/plain"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    for u in json.load(r):
                        out[u["id"]] = u
                break
            except urllib.error.HTTPError as e:
                if e.code == 429: time.sleep(65); continue
                raise
        time.sleep(1.5)
    log(f"api: requested {len(names)}, returned {len(out)}")
    return out

def main(d):
    logf = open(os.path.join(d, "panel_select.log"), "w")
    def log(m): print(m); logf.write(m + "\n"); logf.flush()

    a, ka = month_stats(os.path.join(d, "index_2025-09.tsv.gz"))
    b, kb = month_stats(os.path.join(d, "index_2026-09.tsv.gz"))
    log(f"qualifying games: Sep 2025 {ka:,}, Sep 2026 {kb:,}")
    log(f"players: Sep 2025 {len(a):,}, Sep 2026 {len(b):,}")

    elig = {u for u in a.keys() & b.keys()
            if u not in EXCLUDE and a[u][0] >= MIN_N and b[u][0] >= MIN_N
            and LO <= a[u][1] <= HI}
    log(f"eligible (n>={MIN_N} both months, Sep 2025 mean {LO}-{HI}): {len(elig):,}")
    gain = {u: b[u][1] - a[u][1] for u in elig}
    imp = {u for u in elig if IMP_MIN <= gain[u] <= IMP_MAX}
    ctl = {u for u in elig if abs(gain[u]) <= CTRL_ABS}
    log(f"improvers (+{IMP_MIN}..+{IMP_MAX}): {len(imp):,}; controls (|gain|<={CTRL_ABS}): {len(ctl):,}")

    info = api_users(imp | ctl, log)
    def flagged(u):
        x = info.get(u)
        return (x is None or x.get("tosViolation") or x.get("disabled")
                or x.get("title") == "BOT")
    imp_f = {u for u in imp if not flagged(u)}
    ctl_f = {u for u in ctl if not flagged(u)}
    log(f"after account flags: improvers {len(imp_f):,} (-{len(imp)-len(imp_f)}), "
        f"controls {len(ctl_f):,} (-{len(ctl)-len(ctl_f)})")
    def cur(u): return info[u].get("perfs", {}).get("blitz", {}).get("rating")
    imp_p = {u for u in imp_f if cur(u) is not None and cur(u) >= a[u][1] + PERSIST}
    log(f"after persistence gate (current blitz >= Sep 2025 mean + {PERSIST}): "
        f"improvers {len(imp_p):,} (-{len(imp_f)-len(imp_p)})")

    rng = random.Random(SEED)
    order = sorted(imp_p); rng.shuffle(order)
    free = set(ctl_f) - imp_p; pairs = []
    for u in order:
        cands = [c for c in free if abs(a[c][1] - a[u][1]) <= MATCH_ELO
                 and max(a[c][0], a[u][0]) / min(a[c][0], a[u][0]) <= MATCH_NRATIO]
        if not cands: continue
        c = min(cands, key=lambda c: (abs(a[c][1] - a[u][1]), c))
        free.discard(c); pairs.append((u, c))
    log(f"matched pairs: {len(pairs):,} (unmatched improvers {len(imp_p)-len(pairs):,})")
    rng.shuffle(pairs)

    sp = os.path.join(d, "panel_secret.txt")
    if os.path.exists(sp): key = open(sp).read().strip()
    else:
        key = secrets.token_hex(32); open(sp, "w").write(key + "\n")
    def pid(u):
        return "P" + hmac.new(bytes.fromhex(key), u.lower().encode(),
                              hashlib.sha256).hexdigest()[:10]

    with open(os.path.join(d, "panel_ranks_private.csv"), "w", newline="") as fp, \
         open(os.path.join(d, "panel_ranks.csv"), "w", newline="") as fc, \
         open(os.path.join(d, "panel_key.csv"), "w", newline="") as fk:
        wp, wc, wk = csv.writer(fp), csv.writer(fc), csv.writer(fk)
        wp.writerow(["rank", "pair", "group", "id", "username", "n_2509", "mean_2509",
                     "n_2609", "mean_2609", "gain", "current_blitz"])
        wc.writerow(["rank", "pair", "group", "id"])
        wk.writerow(["id", "username"])
        r = 0
        for k, (u, c) in enumerate(pairs, 1):
            for g, x in (("improver", u), ("control", c)):
                r += 1
                wp.writerow([r, k, g, pid(x), x, a[x][0], round(a[x][1], 1), b[x][0],
                             round(b[x][1], 1), round(gain[x], 1), cur(x)])
                wc.writerow([r, k, g, pid(x)])
                wk.writerow([pid(x), x])
    ids = [pid(x) for p in pairs for x in p]
    assert len(set(ids)) == len(ids), "id collision"
    log(f"wrote {len(pairs)} ranked pairs; pairs 1-40 are the primary panel, "
        f"41-80 the pre-declared extension ({'available' if len(pairs) >= 80 else 'NOT fully available'})")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/panel")
