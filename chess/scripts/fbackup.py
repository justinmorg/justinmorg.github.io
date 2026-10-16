#!/usr/bin/env python3
"""Archive a group F export ("Copy my F results as JSON") into chess/data/f_results/.

  fbackup.py export.json [YYYY-MM-DD]

Refuses to write unless the new export is a superset of the latest archived
one: every (card key, ply) answered before must still be present with the
same answer and timestamp. A smaller export means the browser lost data -
keep the older file and investigate rather than overwriting history.
"""
import sys, os, json, glob, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "..", "data", "f_results")


def index(rows):
    return {(c["key"], s["ply"]): (s["a"], s["ts"]) for c in rows for s in c["steps"]}


def main():
    new = json.load(open(sys.argv[1]))
    day = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().isoformat()
    os.makedirs(DIR, exist_ok=True)
    prev = sorted(glob.glob(os.path.join(DIR, "f_results_*.json")))
    n_new = index(new)
    if prev:
        n_old = index(json.load(open(prev[-1])))
        lost = [k for k in n_old if n_old[k] != n_new.get(k)]
        if lost:
            sys.exit(f"REFUSING: {len(lost)} decisions in {os.path.basename(prev[-1])} "
                     f"are missing or changed in the new export, e.g. {lost[:3]}")
        print(f"superset of {os.path.basename(prev[-1])}: +{len(n_new) - len(n_old)} decisions")
    keys = [c["key"] for c in new]
    if len(keys) != len(set(keys)):
        sys.exit("REFUSING: duplicate card keys in export")
    out = os.path.join(DIR, f"f_results_{day}.json")
    json.dump(new, open(out, "w"), indent=1)
    ts = [s["ts"] for c in new for s in c["steps"]]
    first = datetime.datetime.fromtimestamp(min(ts) / 1000, datetime.timezone.utc)
    print(f"wrote {out}: {len(new)} cards, {len(n_new)} decisions, earliest ts {first:%Y-%m-%d %H:%M} UTC")


if __name__ == "__main__":
    main()
