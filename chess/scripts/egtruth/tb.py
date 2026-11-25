#!/usr/bin/env python3
"""egtruth/tb — Lichess 7-man tablebase answer for every <= 7-man endgame
position in rows.csv.gz (both sides' moves). Resumable; writes one JSON line
per position to OUT.jsonl (gzip it before committing).

    python3 tb.py rows.csv.gz OUT.jsonl [workers=3]

Line: {"k": first four FEN fields, "cat": side-to-move category,
       "m": {uci: [category after move (opponent POV, API convention), dtz, dtm]}}
"""
import sys, os, csv, gzip, json, time, threading, queue, urllib.request, urllib.parse
import chess


def key(fen):
    return " ".join(fen.split()[:4])


def fetch(k):
    url = "https://tablebase.lichess.ovh/standard?fen=" + urllib.parse.quote(k + " 0 1")
    for attempt in range(10):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.load(r)
            return {"k": k, "cat": d["category"],
                    "m": {m["uci"]: [m["category"], m.get("dtz"), m.get("dtm")] for m in d["moves"]}}
        except urllib.error.HTTPError as e:
            time.sleep(60 if e.code == 429 else 2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def main(rows, out, workers=3):
    want = []
    seen = set()
    with gzip.open(rows, "rt") as fh:
        for r in csv.DictReader(fh):
            if int(r["men"]) <= 7:
                k = key(r["fen"])
                if k not in seen:
                    seen.add(k)
                    want.append(k)
    done = set()
    if os.path.exists(out):
        for line in open(out):
            try:
                done.add(json.loads(line)["k"])
            except Exception:
                pass
    todo = [k for k in want if k not in done]
    print(len(want), "positions,", len(todo), "to fetch", flush=True)
    q = queue.Queue()
    for k in todo:
        q.put(k)
    lock = threading.Lock()
    fo = open(out, "a")
    cnt = [0]

    def work():
        while True:
            try:
                k = q.get_nowait()
            except queue.Empty:
                return
            d = fetch(k)
            if d is not None:
                with lock:
                    fo.write(json.dumps(d, separators=(",", ":")) + "\n")
                    cnt[0] += 1
                    if cnt[0] % 500 == 0:
                        fo.flush()
                        print(cnt[0], time.strftime("%H:%M:%S"), flush=True)
            time.sleep(0.05)

    ts = [threading.Thread(target=work) for _ in range(workers)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    fo.close()
    print("done", cnt[0], flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
