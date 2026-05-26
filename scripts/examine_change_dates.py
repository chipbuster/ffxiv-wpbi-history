#!/usr/bin/env python3
"""
Correlates FFXIV patch release dates with world congestion status-change notices.

The ConsoleGamesWiki Patches HTML is cached locally; a fresh copy is fetched
automatically when the cached copy is more than 14 days old. The cache file
records its fetch date in an HTML comment on the first line.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

FILE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WIKI_URL = "https://ffxiv.consolegameswiki.com/wiki/Patches"
HTML_CACHE_PATH = FILE_DIR / "wiki_patches.html"
WORLD_HISTORY_PATH = FILE_DIR.parent / "data" / "world_history.jsonl"
PATCH_DATES_PATH = FILE_DIR.parent / "data" / "patch_dates.jsonl"

WPBI_INTRODUCED = date(2017, 5, 17)
MAX_CACHE_AGE = timedelta(days=14)

CACHE_TIMESTAMP_RE = re.compile(r"<!--\s*cached:\s*(\d{4}-\d{2}-\d{2})\s*-->")

PATCH_DATE_REGEX = re.compile(
    r"""(?P<patch>\b\d+\.\d{1,2}[a-z]?\b)\s*[-–]\s*(?P<date>\d{1,2}\s+
        (?:January|February|March|April|May|June|July|August|September|October|November|December)
        \s+\d{4})""",
    re.IGNORECASE | re.VERBOSE,
)


# ── HTML fetch & cache ────────────────────────────────────────────────────────


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ffxiv-patch-scraper/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _load_cache(cache_path: Path) -> Optional[str]:
    """Return cached HTML body (without the timestamp line) if fresh, else None."""
    if not cache_path.exists():
        return None
    text = cache_path.read_text(encoding="utf-8")
    first_line, _, rest = text.partition("\n")
    m = CACHE_TIMESTAMP_RE.fullmatch(first_line.strip())
    if not m:
        return None
    cached_date = date.fromisoformat(m.group(1))
    if date.today() - cached_date > MAX_CACHE_AGE:
        return None
    return rest


def _save_cache(cache_path: Path, html: str):
    stamp = f"<!-- cached: {date.today().isoformat()} -->\n"
    cache_path.write_text(stamp + html, encoding="utf-8")


def get_wiki_html(url: str, cache_path: Path, force_refresh: bool = False) -> str:
    if not force_refresh:
        cached = _load_cache(cache_path)
        if cached is not None:
            print(f"Using cached HTML ({cache_path})", file=sys.stderr)
            return cached
    print(f"Fetching {url} ...", file=sys.stderr)
    html = _fetch_html(url)
    _save_cache(cache_path, html)
    return html


# ── Patch date extraction ─────────────────────────────────────────────────────


def _normalize_html(s: str) -> str:
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("&ndash;", "-").replace("&mdash;", "-")
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def extract_patch_dates(html: str) -> List[Tuple[str, date]]:
    """Return ordered, deduplicated [(patch_version, release_date)] pairs."""
    text = _normalize_html(html)
    seen: set = set()
    results = []
    for patch_str, date_str in PATCH_DATE_REGEX.findall(text):
        key = (patch_str.strip(), date_str.strip())
        if key not in seen:
            seen.add(key)
            d = datetime.strptime(date_str.strip(), "%d %B %Y").date()
            results.append((patch_str.strip(), d))
    return results


# ── World history loading ─────────────────────────────────────────────────────

_SEED_STATUSES = {"PRE_WPBI", "NEW"}


def load_change_dates(path: Path) -> List[date]:
    """Return the unique dates on which any world changed status, excluding
    the initial PRE_WPBI/NEW seed events that don't correspond to notices."""
    seen: set = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            for event in record["history"]:
                if event["status"] not in _SEED_STATUSES:
                    seen.add(date.fromisoformat(event["date"]))
    return sorted(seen)


# ── Correlation & output ──────────────────────────────────────────────────────


def correlate_and_print(patch_pairs: List[Tuple[str, date]], notice_dates: List[date]):
    patch_date_map = {d: patch for patch, d in patch_pairs if d >= WPBI_INTRODUCED}
    congestion_set = set(notice_dates)
    output: dict = {}

    for d in sorted(patch_date_map):
        patch = patch_date_map[d]
        if d in congestion_set:
            output[d] = (patch, "●")  # same-day
            congestion_set.discard(d)
        elif (d - timedelta(days=1)) in congestion_set:
            output[d] = (patch, "↑")  # status change 1 day before patch
            congestion_set.discard(d - timedelta(days=1))
        elif (d + timedelta(days=1)) in congestion_set:
            output[d] = (patch, "↓")  # status change 1 day after patch
            congestion_set.discard(d + timedelta(days=1))
        else:
            output[d] = (patch, "")

    for d in congestion_set:
        output[d] = (None, "❖")  # status change unrelated to any patch

    for d in sorted(output):
        patch, symbol = output[d]
        print(f"{d:%Y-%m-%d} | {patch or '':<6} | {symbol}")


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(
        description="Correlate FFXIV patch dates with world congestion status changes."
    )
    ap.add_argument(
        "--world-history",
        type=Path,
        default=WORLD_HISTORY_PATH,
        help=f"World history JSONL produced by analyze_world_history.py (default: {WORLD_HISTORY_PATH})",
    )
    ap.add_argument(
        "--url",
        default=WIKI_URL,
        help=f"Wiki URL for patch dates (default: {WIKI_URL})",
    )
    ap.add_argument(
        "--html-cache",
        type=Path,
        default=HTML_CACHE_PATH,
        help=f"Path for the cached wiki HTML (default: {HTML_CACHE_PATH})",
    )
    ap.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-fetch the wiki HTML even if the cache is still fresh.",
    )
    ap.add_argument(
        "--patch-dates",
        type=Path,
        default=PATCH_DATES_PATH,
        help=f"Write patch dates as JSONL to this path (default: {PATCH_DATES_PATH}).",
    )
    ap.add_argument(
        "--patch-dates-only",
        action="store_true",
        help="Only fetch and write patch dates; skip loading status notices and correlation.",
    )
    args = ap.parse_args()

    html = get_wiki_html(args.url, args.html_cache, force_refresh=args.refresh)
    patch_pairs = extract_patch_dates(html)

    with open(args.patch_dates, "w", encoding="utf-8") as f:
        for patch, d in patch_pairs:
            f.write(json.dumps({"patch": patch, "date": d.isoformat()}) + "\n")
    print(
        f"Wrote {len(patch_pairs)} patch dates to {args.patch_dates}", file=sys.stderr
    )

    if args.patch_dates_only:
        return

    notice_dates = load_notice_dates(args.status_notices)
    correlate_and_print(patch_pairs, notice_dates)


if __name__ == "__main__":
    main()
