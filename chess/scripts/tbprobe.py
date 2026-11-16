#!/usr/bin/env python3
"""tbprobe — Lichess tablebase lookups (<= 7 men) with a committed cache.

    probe(fen) -> {"category": win|draw|loss|..., "moves": {uci: {"san", "category", "dtm", "dtz"}}}

`category` is from the side to move's point of view; each move's `category`
is from the point of view of the side to move AFTER it (the API convention),
so a move that keeps a win has category "loss".

The cache (chess/study/tb_cache.json) is committed so every deck rebuilds
offline and byte-identically. Keys are the first four FEN fields.
"""
import os, json, time, urllib.request, urllib.parse
import chess

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "study", "tb_cache.json")
_c = None
_dirty = 0
_used = set()
FLIP = {"win": "loss", "loss": "win", "draw": "draw", "cursed-win": "blessed-loss",
        "blessed-loss": "cursed-win", "maybe-win": "maybe-loss", "maybe-loss": "maybe-win", "unknown": "unknown"}


def _load():
    global _c
    if _c is None:
        _c = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    return _c


def save():
    global _dirty
    if _c is not None and _dirty:
        json.dump(_c, open(CACHE, "w"), sort_keys=True, separators=(",", ":"))
        _dirty = 0


def save_pruned():
    """Write only the entries probed in this run (call at the end of a full build)."""
    global _c, _dirty
    c = _load()
    _c = {k: c[k] for k in sorted(_used) if k in c}
    _dirty = 1
    save()


def key(fen):
    return " ".join(fen.split()[:4])


def probe(fen, offline=False):
    global _dirty
    c = _load()
    k = key(fen)
    _used.add(k)
    if k in c:
        return c[k]
    if offline:
        raise KeyError("not in tablebase cache: " + k)
    b = chess.Board(fen)
    assert chess.popcount(b.occupied) <= 7, "more than 7 men: " + fen
    url = "https://tablebase.lichess.ovh/standard?fen=" + urllib.parse.quote(k + " 0 1")
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                d = json.load(r)
            break
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError("tablebase unreachable for " + fen)
    out = {"category": d["category"], "dtm": d.get("dtm"),
           "order": [m["uci"] for m in d["moves"]],      # best first, as the API returns them
           "moves": {m["uci"]: {"san": m["san"], "category": m["category"], "dtm": m.get("dtm"), "dtz": m.get("dtz")}
                     for m in d["moves"]}}
    c[k] = out
    _dirty += 1
    if _dirty >= 25:
        save()
    time.sleep(0.12)
    return out


def result_white(fen):
    """'W' / 'D' / 'B' from White's point of view (50-move subtleties count as draws)."""
    p = probe(fen)
    cat = p["category"]
    stm_white = fen.split()[1] == "w"
    if cat == "win":
        return "W" if stm_white else "B"
    if cat == "loss":
        return "B" if stm_white else "W"
    return "D"


def keeping_moves(fen):
    """Moves by the side to move that keep the tablebase result (win stays a
    win, draw stays a draw). Returns (goal, {uci: info}, {uci: outcome_for_mover})."""
    p = probe(fen)
    goal = p["category"]
    assert goal in ("win", "draw"), (goal, fen)
    keep, others = {}, {}
    for u, m in p["moves"].items():
        mine = FLIP.get(m["category"], "unknown")
        if mine == goal:
            keep[u] = m
        else:
            others[u] = "draw" if mine in ("draw", "cursed-win", "blessed-loss") else mine
    return goal, keep, others


if __name__ == "__main__":
    for f in ["8/8/8/6k1/1P6/8/8/7K w - - 0 1", "8/8/8/6k1/1P6/8/8/7K b - - 0 1",
              "6K1/4k1P1/8/8/8/8/7r/5R2 w - - 0 1", "4k3/R7/8/3KP3/8/8/8/1r6 b - - 0 1"]:
        p = probe(f)
        print(f, p["category"], result_white(f), {u: (m["san"], m["category"]) for u, m in list(p["moves"].items())[:6]})
    save()
