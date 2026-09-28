"""Crawl Virginia Tech's official TAS/StatCrew game XML from statistics.hokiesports.com.

For each season: read the hokiesports.com schedule page, collect box score IDs, download
  https://statistics.hokiesports.com/api/v1/game/xml/<id>
into hokiesports/raw/<id>.xml, and parse it with parse_tas.py into data/hokiesports/.

Usage:
    python crawl_hokiesports.py 1987 2002             # inclusive season range
    python crawl_hokiesports.py 1998 1998 --dry-run  # list IDs only, no game downloads
    options: --delay 2.0  --force  --retry-missing  --no-parse

Coverage notes (checked Sept 2026):
  * XML exists for 1987 (ID 5120) through part of 2020 (last seen ~5540). From late 2020 on,
    box scores are served by wmt.games in a different format; those IDs return 404 here and
    are recorded as no_xml. CFBD already covers those seasons.
  * Some games have no XML at all (e.g. 2002 West Virginia; most of 2005-2007). Those
    games also have no box score link on the schedule page.
  * Box score IDs are mostly sequential but not contiguous, so the schedule pages, not an
    ID range, are the index.

Politeness: one request at a time, --delay seconds between requests (default 2.0),
exponential backoff on 429/5xx, and games already on disk are skipped. hokiesports/manifest.csv
records every ID seen and its status, so reruns only touch what's new or failed.
"""
import argparse, csv, html, os, re, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "hokiesports", "raw")
MANIFEST = os.path.join(HERE, "hokiesports", "manifest.csv")
GAMES = os.path.join(HERE, "data", "hokiesports", "games")
SCHEDULE_URL = "https://hokiesports.com/sports/football/schedule/season/{season}"
XML_URL = "https://statistics.hokiesports.com/api/v1/game/xml/{id}"
UA = "vt-football-archive/1.0 (personal research; github.com/justinmorg)"
FIELDS = ["season", "id", "label", "status", "note"]
BOX_RE = re.compile(r'href="/boxscore/(\d+)"[^>]*aria-label="([^"]*)"')

sys.path.insert(0, HERE)
import parse_tas  # noqa: E402


class Fetcher:
    def __init__(self, delay):
        self.delay, self.last, self.count = delay, 0.0, 0

    def get(self, url, tries=4):
        """Returns (status, bytes). 404 -> (404, None). Retries 429/5xx/network errors."""
        for attempt in range(tries):
            wait = self.delay - (time.time() - self.last)
            if wait > 0: time.sleep(wait)
            self.last = time.time(); self.count += 1
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                if e.code == 404: return 404, None
                if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1: return e.code, None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == tries - 1: return 0, str(e).encode()
            backoff = self.delay * (2 ** (attempt + 1))
            print(f"    retry in {backoff:.0f}s: {url}")
            time.sleep(backoff)


def load_manifest():
    if not os.path.exists(MANIFEST): return {}
    with open(MANIFEST, newline="") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def save_manifest(m):
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    rows = sorted(m.values(), key=lambda r: (int(r["season"]), int(r["id"])))
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


def season_ids(fetcher, season):
    status, body = fetcher.get(SCHEDULE_URL.format(season=season))
    if status != 200 or not body:
        print(f"  schedule {season}: HTTP {status}"); return []
    seen, out = set(), []
    for gid, label in BOX_RE.findall(body.decode("utf-8", "replace")):
        if gid not in seen:
            seen.add(gid); out.append((gid, html.unescape(label).replace(" - Box Score", "")))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("start", type=int); ap.add_argument("end", type=int)
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests (default 2)")
    ap.add_argument("--force", action="store_true", help="re-download and re-parse games already saved")
    ap.add_argument("--retry-missing", action="store_true", help="re-try IDs previously recorded as no_xml/error")
    ap.add_argument("--no-parse", action="store_true", help="save raw XML only")
    ap.add_argument("--dry-run", action="store_true", help="read schedules and list IDs; download no games")
    a = ap.parse_args()

    manifest, fetcher = load_manifest(), Fetcher(a.delay)
    os.makedirs(RAW, exist_ok=True)
    totals = dict(saved=0, skipped=0, no_xml=0, error=0)
    try:
        for season in range(a.start, a.end + 1):
            ids = season_ids(fetcher, season)
            print(f"{season}: {len(ids)} box score links")
            for gid, label in ids:
                prev = manifest.get(gid, {})
                raw = os.path.join(RAW, f"{gid}.xml")
                parsed = os.path.exists(os.path.join(GAMES, f"{gid}.parquet"))
                row = dict(season=season, id=gid, label=label, status=prev.get("status", ""), note=prev.get("note", ""))
                manifest[gid] = row
                if a.dry_run:
                    print(f"  {gid}  {label}  [{row['status'] or 'new'}]"); continue
                if not a.force and os.path.exists(raw) and (parsed or a.no_parse):
                    row["status"] = row["status"] or "saved"; totals["skipped"] += 1; continue
                if not a.force and not a.retry_missing and prev.get("status") in ("no_xml", "error"):
                    totals["skipped"] += 1; continue

                if a.force or not os.path.exists(raw):
                    status, body = fetcher.get(XML_URL.format(id=gid))
                    if status == 404 or (body and not body.lstrip().startswith(b"<fbgame")):
                        row.update(status="no_xml", note=f"HTTP {status}"); totals["no_xml"] += 1
                        print(f"  {gid} {label}: no XML"); continue
                    if status != 200:
                        row.update(status="error", note=f"HTTP {status}"); totals["error"] += 1
                        print(f"  {gid} {label}: HTTP {status}"); continue
                    ET.fromstring(body)  # fail loudly before writing a bad file
                    with open(raw, "wb") as f: f.write(body)
                if not a.no_parse:
                    try:
                        print("  ", end=""); parse_tas.parse(raw, gid)
                    except Exception as e:
                        row.update(status="parse_error", note=repr(e)[:200]); totals["error"] += 1
                        print(f"  {gid} {label}: parse error {e!r}"); continue
                row.update(status="saved", note=""); totals["saved"] += 1
            save_manifest(manifest)  # checkpoint after each season
    except KeyboardInterrupt:
        print("\ninterrupted; manifest saved")
    finally:
        save_manifest(manifest)
    print(f"done: {totals} ({fetcher.count} HTTP requests)")


if __name__ == "__main__":
    main()
