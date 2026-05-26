#!/usr/bin/env python3
"""
Fetches FFXIV patch release dates from the ConsoleGamesWiki Patches page and
writes them to a JSONL file. The wiki HTML is cached locally; a fresh copy is
fetched automatically when the cached copy is more than 14 days old.
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
HTML_CACHE_PATH = FILE_DIR.parent / "data" / "wiki_patches.html"
PATCH_DATES_PATH = FILE_DIR.parent / "data" / "patch_dates.jsonl"

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


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(
        description="Fetch FFXIV patch dates from the ConsoleGamesWiki and write to JSONL."
    )
    ap.add_argument(
        "--url",
        default=WIKI_URL,
        help=f"Wiki URL to fetch (default: {WIKI_URL})",
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
        help=f"Output JSONL of patch dates (default: {PATCH_DATES_PATH})",
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


if __name__ == "__main__":
    main()
