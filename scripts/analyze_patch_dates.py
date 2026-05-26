#!/usr/bin/env python3
"""
Correlates FFXIV patch release dates with world congestion status-change notices.

Reads patch dates from a JSONL file (produced by scrape_patch_dates.py) and
world history from a JSONL file (produced by analyze_world_history.py).
"""

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

FILE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WORLD_HISTORY_PATH = FILE_DIR.parent / "data" / "world_history.jsonl"
PATCH_DATES_PATH = FILE_DIR.parent / "data" / "patch_dates.jsonl"

WPBI_INTRODUCED = date(2017, 5, 17)

_SEED_STATUSES = {"PRE_WPBI", "NEW"}


def load_patch_dates(path: Path) -> List[Tuple[str, date]]:
    """Return ordered [(patch_version, release_date)] pairs from JSONL."""
    pairs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            pairs.append((record["patch"], date.fromisoformat(record["date"])))
    return pairs


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

    print("This prints out the dates of World Status Changes AND Patches.")
    print("If there is a patch number and a symbol, the status change occurred")
    print("within 1 day of the patch. A symbol without a patch number means the")
    print("status change is not related to a patch, and a patch number without")
    print("a symbol means the patch came out without a status change.")
    print("Date       | Patch  | Symbol")
    print("           | XX     | ●  (same-day status change)")
    print("           | XX     | ↑  (status change 1 day before patch)")
    print("           | XX     | ↓  (status change 1 day after patch)")
    print("           |        | ❖  (status change unrelated to any patch)")
    print("           | XX     |    (Patch without status change)")
    print("-" * 40)
    for d in sorted(output):
        patch, symbol = output[d]
        print(f"{d:%Y-%m-%d} | {patch or '':<6} | {symbol}")


def main():
    ap = argparse.ArgumentParser(
        description="Correlate FFXIV patch dates with world congestion status changes."
    )
    ap.add_argument(
        "--patch-dates",
        type=Path,
        default=PATCH_DATES_PATH,
        help=f"JSONL of patch dates produced by scrape_patch_dates.py (default: {PATCH_DATES_PATH})",
    )
    ap.add_argument(
        "--world-history",
        type=Path,
        default=WORLD_HISTORY_PATH,
        help=f"World history JSONL produced by analyze_world_history.py (default: {WORLD_HISTORY_PATH})",
    )
    args = ap.parse_args()

    patch_pairs = load_patch_dates(args.patch_dates)
    change_dates = load_change_dates(args.world_history)
    correlate_and_print(patch_pairs, change_dates)


if __name__ == "__main__":
    main()
