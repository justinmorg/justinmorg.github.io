#!/usr/bin/env bash
# Thread 9, step 3: extract pass. Streams one month of the Lichess open
# database again and keeps the full game text of every rated 3+2/5+0
# non-arena game in which a listed panel player played. Never writes the
# decompressed month to disk.
#
#   bash panel_extract.sh 2025-09 /home/claude/panel/extract_names.txt /home/claude/panel [FROM_BYTE]
#
# FROM_BYTE resumes after a dropped connection. The database files are
# multi-frame zstd (frames ~4.7 MB), so the stream can restart at any frame
# boundary: the first frame magic at or after FROM_BYTE is found and the
# stream starts there, into extract_<M>.from<OFFSET>.pgn.gz. Start well
# before the cut (e.g. 200 MB): the overlap is deduplicated by game id in
# panel_anon.py, and the partial game at each cut is discarded there.
#
# names file: one lowercase username per line (PRIVATE).
# Output: <outdir>/extract_<YYYY-MM>.pgn.gz -- still carries real usernames;
# panel_anon.py turns it into the committable form.
set -euo pipefail
M="$1"; NAMES="$2"; OUT="${3:-/home/claude/panel}"
URL="https://database.lichess.org/standard/lichess_db_standard_rated_${M}.pgn.zst"
FROM="${4:-}"
RANGE=()
if [ -n "$FROM" ]; then
  OFF=$(curl -sS --fail -r "${FROM}-$((FROM + 20000000))" "$URL" | python3 -c '
import sys; d = sys.stdin.buffer.read(); i = d.find(b"\x28\xb5\x2f\xfd")
sys.exit("no frame magic found") if i < 0 else print(int(sys.argv[1]) + i)' "$FROM")
  RANGE=(-r "${OFF}-"); TAGP=".from${OFF}"
else TAGP=""; fi
DST="$OUT/extract_${M}${TAGP}.pgn.gz"
rm -f "$DST" "$OUT/extract_${M}${TAGP}.done"
echo "${OFF:-0}" > "$OUT/extract_${M}${TAGP}.offset"   # with .bytes: where a cut stream stopped

curl -sS --fail --retry 3 "${RANGE[@]}" "$URL" \
| python3 -c '
import sys, zstandard
class Count:
    def __init__(s, f, path): s.f, s.n, s.path, s.last = f, 0, path, 0
    def read(s, k=-1):
        b = s.f.read(k); s.n += len(b)
        if s.n - s.last > 50_000_000:
            open(s.path, "w").write(str(s.n)); s.last = s.n
        return b
src = Count(sys.stdin.buffer, sys.argv[1])
r = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(src, read_size=1<<20)
w = sys.stdout.buffer
while True:
    b = r.read(1<<22)
    if not b: break
    w.write(b)
' "$OUT/extract_${M}${TAGP}.bytes" \
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
END { print kept > "/dev/stderr" }' 2> "$OUT/extract_${M}${TAGP}.kept" \
| gzip -6 > "$DST"

printf 'month=%s from=%s games_kept=%s finished=%s\n' "$M" "${OFF:-0}" \
  "$(cat "$OUT/extract_${M}${TAGP}.kept")" "$(date -u +%FT%TZ)" | tee "$OUT/extract_${M}${TAGP}.done"
