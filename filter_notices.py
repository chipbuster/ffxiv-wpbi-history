import json
import datetime

def parse_notice_date(notice):
    fmt_candidates = ["%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y", "%Y-%m-%d"]
    if "date" in notice and notice["date"]:
        for fmt in fmt_candidates:
            try:
                return datetime.datetime.strptime(notice["date"], fmt).date()
            except Exception:
                pass
    raise ValueError("Could not parse date from notice.")

output_is = set()
urls = set()
phrase = "Congested/Preferred".lower()

with open("notices.jsonl", encoding="utf-8") as fin:
    notices = [ json.loads(l) for l in fin.readlines() ]

# The scraped data is not 100% clean and may include duplicate posts. To avoid
# these when filtering, we only add posts that correspond to unique URLs.

for (i, n) in enumerate(notices):
    text = n["body"].lower()
    if phrase in text and n["url"] not in urls:
        output_is.add(i)
        urls.add(n["url"])

output = [ notices[i] for i in output_is ] 
output.sort(key=parse_notice_date)

with open("filtered.jsonl", "w", encoding="utf-8") as fout:
    for obj in output:
        fout.write(json.dumps(obj, ensure_ascii=False))
        fout.write("\n")
