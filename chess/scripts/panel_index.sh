#!/usr/bin/env bash
# Thread 9, step 1: header-only index pass over one month of the Lichess open
# database. Streams the .pgn.zst, never writes the decompressed month to disk,
# keeps one row per rated 3+2 / 5+0 game, no move text.
#
#   bash panel_index.sh 2025-09 /home/claude/panel
#
# Output: <outdir>/index_<YYYY-MM>.tsv.gz  (+ .done marker with counts)
# Columns: gid date time white black welo belo wdiff bdiff result tc arena termination
#   arena = 1 if Event is a tournament game (README corpus filter is non-arena)
#
# Contains real usernames: NOT for committing to the (publicly served) repo.
set -euo pipefail
M="$1"; OUT="${2:-/home/claude/panel}"
mkdir -p "$OUT"
URL="https://database.lichess.org/standard/lichess_db_standard_rated_${M}.pgn.zst"
DST="$OUT/index_${M}.tsv.gz"
rm -f "$DST" "$OUT/index_${M}.done"

curl -sS --fail --retry 3 "$URL" \
| python3 -c '
import sys, zstandard
d = zstandard.ZstdDecompressor(max_window_size=2**31)
r = d.stream_reader(sys.stdin.buffer, read_size=1<<20)
w = sys.stdout.buffer
while True:
    b = r.read(1<<22)
    if not b: break
    w.write(b)
' \
| LC_ALL=C grep -E '^\[(Event|Site|White|Black|Result|UTCDate|UTCTime|WhiteElo|BlackElo|WhiteRatingDiff|BlackRatingDiff|TimeControl|Termination) ' \
| LC_ALL=C mawk -v OFS='\t' '
function flush() {
  if (have && (tc == "180+2" || tc == "300+0") && ev ~ /^Rated Blitz/)
    print gid, dt, tm, wh, bl, we, be, wd, bd, res, tc, (ev ~ /tournament/ ? 1 : 0), term
  have = 0; gid=dt=tm=wh=bl=we=be=wd=bd=res=tc=term=""
}
{
  key = substr($1, 2)
  v = $0; sub(/^\[[A-Za-z]+ "/, "", v); sub(/"\]$/, "", v)
  if (key == "Event") { flush(); ev = v; have = 1; total++ }
  else if (key == "Site") { n = split(v, p, "/"); gid = p[n] }
  else if (key == "White") wh = v
  else if (key == "Black") bl = v
  else if (key == "Result") res = v
  else if (key == "UTCDate") dt = v
  else if (key == "UTCTime") tm = v
  else if (key == "WhiteElo") we = v
  else if (key == "BlackElo") be = v
  else if (key == "WhiteRatingDiff") wd = v
  else if (key == "BlackRatingDiff") bd = v
  else if (key == "TimeControl") tc = v
  else if (key == "Termination") term = v
}
END { flush(); print total > "/dev/stderr" }' 2> "$OUT/index_${M}.total" \
| gzip -1 > "$DST"

KEPT=$(gzip -dc "$DST" | wc -l)
LAST=$(gzip -dc "$DST" | cut -f2 | sort | tail -1)
printf 'month=%s games_seen=%s kept=%s last_date=%s finished=%s\n' \
  "$M" "$(cat "$OUT/index_${M}.total")" "$KEPT" "$LAST" "$(date -u +%FT%TZ)" \
  | tee "$OUT/index_${M}.done"
