#!/usr/bin/env bash
# Keep resuming panel_extract.sh after dropped connections until a part
# finishes (.done written). Each retry restarts 50 MB before where the cut
# part had read to; panel_anon.py dedupes the overlap.
#   bash panel_extract_loop.sh 2025-09 NAMES OUTDIR FROM_BYTE
set -uo pipefail
M="$1"; NAMES="$2"; OUT="$3"; FROM="$4"
HERE="$(cd "$(dirname "$0")" && pwd)"
for try in 1 2 3 4 5 6 7 8; do
  bash "$HERE/panel_extract.sh" "$M" "$NAMES" "$OUT" "$FROM" && exit 0
  last=$(ls -t "$OUT"/extract_"$M".from*.offset | head -1); base="${last%.offset}"
  off=$(cat "$last"); got=$(cat "$base.bytes" 2>/dev/null || echo 0)
  FROM=$(( off + got - 50000000 )); [ "$FROM" -lt "$off" ] && FROM=$off
  echo "retry $try: cut after $got bytes from $off; resuming near $FROM" >&2
done
exit 1
