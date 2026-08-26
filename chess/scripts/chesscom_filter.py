#!/usr/bin/env python3
"""Filter raw chess.com monthly PGN exports down to a clean blitz corpus.

chess.com exports mix everything the account played that month into one file:
several time-control classes (each with its OWN rating pool), board variants,
and daily correspondence games. None of that is comparable to the Lichess
corpus, and the rating tags in particular are meaningless once pools are mixed.

Usage:
    python3 chesscom_filter.py OUT.pgn IN1.pgn [IN2.pgn ...] [--tc 180+2]

Keeps a game only if all of:
  - Event == "Live Chess"      (drops variants and "Let's Play!" daily)
  - time-control class is blitz
  - the game has at least one move

Time-control class uses estimated duration = base + 40*increment:
    < 180s  bullet      180-599s  blitz      >= 600s  rapid
Daily controls (the "1/259200" form) are dropped outright.

Deduplicates on the chess.com game id parsed from the Link tag. Earlier files
win on collision, matching merge.py's convention.

Injects a GameId tag, which chess.com does not emit but the rest of the
pipeline requires (annot_inc.py resumes by GameId, merge.py dedupes by it, and
the drill tick keys are "{mode}-{gid}-{ply}"). Form is "cc" + the numeric id
from Link, e.g. cc140737090058:

  - no hyphen, so it can't corrupt the "-"-delimited drill tick keys
  - the "cc" prefix makes provenance visible in a tick key at a glance
  - 14 chars vs Lichess's 8, so it cannot collide with a Lichess GameId

Prints a report to stderr; writes PGN to OUT.pgn.
"""
import re
import sys
import collections

GAME_SPLIT = re.compile(r"\n(?=\[Event )")
TAG_RE = re.compile(r'^\[(\w+)\s+"(.*)"\]$', re.M)
LINK_RE = re.compile(r"/game/(?:live|daily)/(\d+)")


def tc_class(tc):
    """Return 'bullet' | 'blitz' | 'rapid' | 'daily' | 'unknown'."""
    if not tc:
        return "unknown"
    if "/" in tc:
        return "daily"
    if "+" in tc:
        base, inc = tc.split("+", 1)
    else:
        base, inc = tc, "0"
    try:
        secs = int(base) + 40 * int(inc)
    except ValueError:
        return "unknown"
    if secs < 180:
        return "bullet"
    if secs < 600:
        return "blitz"
    return "rapid"


def games(path):
    txt = open(path, encoding="utf-8", errors="replace").read().strip()
    for chunk in GAME_SPLIT.split(txt):
        if "[Event " not in chunk:
            continue
        yield chunk.strip(), dict(TAG_RE.findall(chunk))


def main(argv):
    want_tc = None
    if "--tc" in argv:
        i = argv.index("--tc")
        want_tc = argv[i + 1]
        del argv[i:i + 2]
    out_path, in_paths = argv[0], argv[1:]

    kept, seen = [], set()
    drop = collections.Counter()
    tc_seen = collections.Counter()

    for path in in_paths:
        for text, tags in games(path):
            tc = tags.get("TimeControl", "")
            cls = tc_class(tc)
            tc_seen[(cls, tc)] += 1

            if tags.get("Event") != "Live Chess":
                drop["non-standard Event (%s)" % tags.get("Event", "?")] += 1
                continue
            if cls != "blitz":
                drop["time-control class: %s" % cls] += 1
                continue
            if want_tc and tc != want_tc:
                drop["TimeControl != %s" % want_tc] += 1
                continue
            m = LINK_RE.search(tags.get("Link", ""))
            gid = m.group(1) if m else None
            if gid is None:
                drop["no parseable Link/game id"] += 1
                continue
            if gid in seen:
                drop["duplicate game id"] += 1
                continue
            # a header-only game with no moves is useless downstream
            body = text[text.rfind("]\n") + 2:].strip()
            if not re.search(r"\d+\.", body):
                drop["no moves"] += 1
                continue
            seen.add(gid)
            if "[GameId " not in text:
                # place it immediately after the last header line
                cut = text.rfind("]\n") + 2
                text = text[:cut] + '[GameId "cc%s"]\n' % gid + text[cut:]
            kept.append((tags.get("UTCDate", ""), tags.get("UTCTime", ""), gid, text))

    kept.sort(key=lambda r: (r[0], r[1], r[2]))
    with open(out_path, "w", encoding="utf-8") as fh:
        for _, _, _, text in kept:
            fh.write(text)
            fh.write("\n\n\n")

    w = sys.stderr.write
    w("read %d file(s)\n" % len(in_paths))
    w("\ntime controls seen (class, tag, count):\n")
    for (cls, tc), n in sorted(tc_seen.items(), key=lambda kv: -kv[1]):
        w("  %-8s %-10s %5d\n" % (cls, tc, n))
    w("\ndropped:\n")
    for reason, n in drop.most_common():
        w("  %5d  %s\n" % (n, reason))
    w("\nkept %d games -> %s\n" % (len(kept), out_path))
    if kept:
        w("date range: %s -> %s\n" % (kept[0][0], kept[-1][0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
