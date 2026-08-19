#!/usr/bin/env python3
"""
merge.py — fold newly annotated games into the canonical 2026 corpus.

Dedupes by GameId (first file wins), sorts chronologically by UTCDate +
UTCTime, and writes movetext as a single line per game to match the
existing corpus formatting.

Usage: python3 merge.py OUT.pgn IN1.pgn IN2.pgn [...]
"""
import re
import sys

SPLIT = re.compile(r"\n\n+(?=\[Event )")


def tag(text, name, default=""):
    m = re.search(r"\[%s \"([^\"]*)\"\]" % name, text)
    return m.group(1) if m else default


def normalize(text):
    """Split headers from movetext; collapse movetext onto one line."""
    lines = text.strip().split("\n")
    headers, i = [], 0
    while i < len(lines) and lines[i].startswith("["):
        headers.append(lines[i])
        i += 1
    moves = " ".join(l.strip() for l in lines[i:] if l.strip())
    moves = re.sub(r"\s+", " ", moves).strip()
    return "\n".join(headers) + "\n\n" + moves


def main():
    out_path, in_paths = sys.argv[1], sys.argv[2:]
    seen, games, dupes = set(), [], []
    for p in in_paths:
        text = open(p, encoding="utf-8", errors="replace").read().strip()
        for g in SPLIT.split(text):
            gid = tag(g, "GameId") or tag(g, "Site")
            if gid in seen:
                dupes.append(gid)
                continue
            seen.add(gid)
            games.append((tag(g, "UTCDate"), tag(g, "UTCTime"), gid, normalize(g)))
    games.sort(key=lambda r: (r[0], r[1], r[2]))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(g[3] for g in games) + "\n")
    print("games written : %d" % len(games))
    print("duplicates    : %d %s" % (len(dupes), dupes[:5]))
    print("date range    : %s -> %s" % (games[0][0], games[-1][0]))


if __name__ == "__main__":
    main()
