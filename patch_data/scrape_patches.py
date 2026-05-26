#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
import sys
from typing import List, Tuple
import csv

PATCH_DATE_REGEX = re.compile(
    r"""(?P<patch>\b\d+\.\d{1,2}[a-z]?\b)\s*[-–]\s*(?P<date>\d{1,2}\s+
        (?:January|February|March|April|May|June|July|August|September|October|November|December)
        \s+\d{4})""",
    re.IGNORECASE | re.VERBOSE,
)


def normalize_text(s: str) -> str:
    # Normalize dashes and whitespace
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("&ndash;", "-").replace("&mdash;", "-")
    # Turn <br> into newlines to separate entries
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    # Strip tags
    s = re.sub(r"<[^>]+>", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def extract_pairs(html_text: str) -> List[Tuple[str, str]]:
    text = normalize_text(html_text)
    pairs = PATCH_DATE_REGEX.findall(text)
    # Keep order, drop duplicates
    seen = set()
    ordered = []
    for patch, date in pairs:
        key = (patch.strip(), date.strip())
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def main():
    ap = argparse.ArgumentParser(
        description="Extract FFXIV patch numbers and release dates from ConsoleGamesWiki 'Patches' HTML."
    )
    ap.add_argument("html_path", type=Path, help="Path to the downloaded HTML file.")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("ffxiv_patches.csv"),
        help="Output CSV path (default: ffxiv_patches.csv)",
    )
    args = ap.parse_args()

    if not args.html_path.exists():
        print(f"Error: HTML file not found: {args.html_path}", file=sys.stderr)
        sys.exit(1)

    html_text = args.html_path.read_text(encoding="utf-8", errors="ignore")
    pairs = extract_pairs(html_text)

    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["patch", "date"])
        for patch, date in pairs:
            writer.writerow([patch, date])

    print(f"Wrote {len(pairs)} rows to {args.output}")


if __name__ == "__main__":
    main()
