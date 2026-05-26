import json
import csv
from datetime import datetime, timedelta, date

WPBI_INTRODUCED = date(2017, 5, 17)


def parse_notice_date(notice):
    fmt_candidates = ["%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y", "%Y-%m-%d"]
    if "date" in notice and notice["date"]:
        for fmt in fmt_candidates:
            try:
                return datetime.strptime(notice["date"], fmt).date()
            except Exception:
                pass
    raise ValueError("Could not parse date from notice.")


with open("filtered.jsonl", encoding="utf-8") as fin:
    notices = [json.loads(l) for l in fin.readlines()]

congestion_change_dates = [parse_notice_date(n) for n in notices]

# --- Load patch CSV ---
patch_dates = {}
with open("ffxiv_patches.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        d = datetime.strptime(row["date"], "%d %B %Y").date()

        if d < WPBI_INTRODUCED:
            continue

        patch_dates[d] = row["patch"]

# --- Load congestion change dates ---
# Example: congestion_change_dates = ["2023-10-03", "2024-04-21", ...]
congestion_dates = congestion_change_dates
congestion_set = set(congestion_dates)

output = {}

for d in sorted(patch_dates.keys()):
    patch = patch_dates[d]
    symbol = ""

    if d in congestion_set:
        output[d] = (patch, "●")  # same-day
        congestion_set.remove(d)
    elif (d - timedelta(days=1)) in congestion_set:
        output[d] = (patch, "↑")  # change occurred 1 day before
        congestion_set.remove(d - timedelta(days=1))
    elif (d + timedelta(days=1)) in congestion_set:
        output[d] = (patch, "↓")  # change occurred 1 day after
        congestion_set.remove(d + timedelta(days=1))
    else:
        output[d] = (patch, "")

# All remaining dates in congestion set are independent from patches
for d in congestion_set:
    if d in patch_dates.keys():
        println(f"What da fu---this should have been removed!  {d}")
    output[d] = (None, "❖")

for d in sorted(output.keys()):
    (patch, symbol) = output[d]
    if patch is None:
        patch = ""
    print(f"{d:%Y-%m-%d} | {patch:<6} | {symbol}")
