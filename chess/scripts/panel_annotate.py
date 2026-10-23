#!/usr/bin/env python3
"""Thread 9, step 4a: annotate panel player-months in rank order.

    python3 panel_annotate.py /home/claude/panel --pairs 1-40 [--lanes 2] [--hours 1.9]

Walks <dir>/pm/manifest.csv in pair order (improver then control, Sep 2025
then Sep 2026) and runs annot_inc.py on each <id>_<yymm>.pgn into
<dir>/ann/<id>_<yymm>_analyzed.pgn, one engine process per lane. annot_inc
resumes by GameId, so killing this and rerunning loses at most one game per
lane. Stops starting new work once --hours has elapsed, so it exits cleanly
inside the 2-hour background limit. A player-month is finished when
annot_inc prints DONE; finished ones are listed in <dir>/ann/done.txt.
"""
import csv, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    a = sys.argv[1:]
    d = a[0]
    lo, hi = map(int, a[a.index("--pairs") + 1].split("-"))
    lanes = int(a[a.index("--lanes") + 1]) if "--lanes" in a else 2
    hours = float(a[a.index("--hours") + 1]) if "--hours" in a else 1.9
    t_end = time.time() + hours * 3600
    ann = os.path.join(d, "ann"); os.makedirs(ann, exist_ok=True)
    donef = os.path.join(ann, "done.txt")
    done = set(open(donef).read().split()) if os.path.exists(donef) else set()
    man = list(csv.DictReader(open(os.path.join(d, "pm", "manifest.csv"))))
    man.sort(key=lambda r: (int(r["pair"]), r["group"] != "improver", r["month"]))
    todo = [f'{r["id"]}_{r["month"]}' for r in man
            if lo <= int(r["pair"]) <= hi and f'{r["id"]}_{r["month"]}' not in done]
    print(f"{len(todo)} player-months to annotate (pairs {lo}-{hi}); {len(done)} already done",
          flush=True)

    def run(pm):
        src = os.path.join(d, "pm", pm + ".pgn")
        dst = os.path.join(ann, pm + "_analyzed.pgn")
        if time.time() >= t_end: return
        while time.time() < t_end:
            budget = max(30, min(600, t_end - time.time()))
            out = subprocess.run([sys.executable, os.path.join(HERE, "annot_inc.py"),
                                  src, dst, str(budget)], capture_output=True, text=True)
            last = (out.stdout.strip().splitlines() or [""])[-1]
            if out.returncode != 0:
                print(f"{pm}: ERROR {out.stderr.strip()[-300:]}", flush=True); return
            if "DONE" in last:
                with open(donef, "a") as f: f.write(pm + "\n")
                print(f"{pm}: {last}  [{time.strftime('%H:%M')}]", flush=True); return
        print(f"{pm}: time budget reached, will resume", flush=True)

    with ThreadPoolExecutor(lanes) as ex:
        for pm in todo:
            if time.time() >= t_end: break
            ex.submit(run, pm)
    n = len(set(open(donef).read().split())) if os.path.exists(donef) else 0
    print(f"finished this run; {n} player-months done in total", flush=True)

if __name__ == "__main__":
    main()
