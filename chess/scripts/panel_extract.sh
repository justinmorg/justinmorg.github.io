#!/usr/bin/env bash
# Thread 9, step 3: extract pass. Streams one month of the Lichess open
# database again and keeps the full game text of every rated 3+2/5+0
# non-arena game in which a listed panel player played. Never writes the
# decompressed month to disk.
#
#   bash panel_extract.sh 2025-09 /home/claude/panel/extract_names.txt /home/claude/panel
#
# names file: one lowercase username per line (PRIVATE).
# Output: <outdir>/extract_<YYYY-MM>.pgn.gz -- still carries real usernames;
# panel_anon.py turns it into the committable form.
set -euo pipefail
M="$1"; NAMES="$2"; OUT="${3:-/home/claude/panel}"
URL="https://database.lichess.org/standard/lichess_db_standard_rated_${M}.pgn.zst"
DST="$OUT/extract_${M}.pgn.gz"
rm -f "$DST" "$OUT/extract_${M}.done"

curl -sS --fail --retry 3 "$URL" \
| python3 -c '
import sys, zstandard
r = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(sys.stdin.buffer, read_size=1<<20)
w = sys.stdout.buffer
while True:
    b = r.read(1<<22)
    if not b: break
    w.write(b)
' \
| LC_ALL=C mawk -v names="$NAMES" '
BEGIN { while ((getline n < names) > 0) want[n] = 1; RS = "" }
/^\[Event / {
  keep = 0
  if ($0 ~ /\[Event "Rated Blitz game"\]/ && $0 ~ /\[TimeControl "(180\+2|300\+0)"\]/ \
      && $0 !~ /\[Termination "(Abandoned|Rules infraction)"\]/) {
    w = ""; b = ""
    if (match($0, /\[White "[^"]*"\]/)) w = tolower(substr($0, RSTART+8, RLENGTH-10))
    if (match($0, /\[Black "[^"]*"\]/)) b = tolower(substr($0, RSTART+8, RLENGTH-10))
    if ((w in want) || (b in want)) keep = 1
  }
  if (keep) { printf "%s\n\n", $0; kept++ }
  next
}
{ if (keep) printf "%s\n\n", $0; keep = 0 }
END { print kept > "/dev/stderr" }' 2> "$OUT/extract_${M}.kept" \
| gzip -6 > "$DST"

printf 'month=%s games_kept=%s finished=%s\n' "$M" "$(cat "$OUT/extract_${M}.kept")" \
  "$(date -u +%FT%TZ)" | tee "$OUT/extract_${M}.done"
