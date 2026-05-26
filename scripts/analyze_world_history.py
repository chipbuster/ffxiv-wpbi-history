import argparse
import datetime
import json
import os
import re
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional

# The WPBI system is announced via a Lodestone Topics post on 2017-05-17
# https://na.finalfantasyxiv.com/lodestone/topics/detail/fee198ff2f37cd22f5b138f7672360440abe9651
WPBI_INTRODUCED = datetime.date(2017, 5, 17)

FILE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WORLD_CREATION_PATH = FILE_DIR.parent / "data" / "world_creation.txt"


class WorldStatus(Enum):
    PRE_WPBI = auto()  # Before world population balancing incentives
    NEW = auto()
    PREFERRED = auto()
    STANDARD = auto()
    CONGESTED = auto()


################################################
# GPT Generated Section to parse notice bodies #
################################################

_HEADING_RE = re.compile(
    r"^▼\s*[A-Za-z]+ to.*\s+(Preferred\+|Preferred|Standard|Congested)\s+Worlds?\b",
    re.IGNORECASE,
)

# World names in FFXIV are single tokens (letters with optional apostrophe/hyphen)
_WORLD_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z'\-]*$")


# Lines that should break/close the current section bucket
def _is_section_break(ln: str) -> bool:
    if not ln:
        return True
    if ln.startswith("▼"):  # any other ▼ heading like "▼New World"
        return True
    if ln.startswith("■"):  # region headers like "■North American Data Center"
        return True
    if ln.lower() in {"older", "newer", "notices"}:
        return True
    if ln.lower().startswith("related news"):
        return True
    if ln.startswith("[") and ln.endswith("]"):  # link titles like "[Follow-up] …"
        return True
    if ln.startswith("http"):
        return True
    # date-only lines like "11/12/2024"
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", ln):
        return True
    # boilerplate / long sentences
    if (
        "For details" in ln
        or "For the current status" in ln
        or "We will continue to observe" in ln
    ):
        return True
    return False


def parse_notice_date(notice):
    fmt_candidates = ["%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y", "%Y-%m-%d"]
    if "date" in notice and notice["date"]:
        for fmt in fmt_candidates:
            try:
                return datetime.datetime.strptime(notice["date"], fmt).date()
            except Exception:
                pass
    raise ValueError("Could not parse date from notice.")


def extract_world_changes(notice):
    """
    Returns (notice_date, new_world, preferred, standard, congested) from a
    Lodestone notice body. "Preferred+" worlds (renamed from "New" in patch 7.3)
    are returned in the new_world bucket.
    - Aggregates across multiple data-center sections.
    - Ignores footer sections like 'Related News'.
    - Only accepts single-token world names (letters with optional ' or -).
    """
    body = (notice.get("body") or "").splitlines()
    # Trim whitespace and skip purely empty lines up-front
    lines = [ln.strip() for ln in body]

    new_world: List[str] = []
    preferred: List[str] = []
    standard: List[str] = []
    congested: List[str] = []

    current_bucket: Optional[List[str]] = None

    for raw in lines:
        ln = raw.strip()
        if not ln:
            # allow empty lines to act as soft boundaries
            current_bucket = (
                current_bucket  # no-op; keeps bucket open across blank lines
            )
            continue

        # Heading?
        m = _HEADING_RE.match(ln)
        if m:
            label = m.group(1).lower()
            if label == "preferred+" or label == "new":
                current_bucket = new_world
            elif label == "preferred":
                current_bucket = preferred
            elif label == "standard":
                current_bucket = standard
            elif label == "congested":
                current_bucket = congested
            continue

        # Other boundaries or footers?
        if _is_section_break(ln):
            current_bucket = None
            continue

        # Collect only if we're in a bucket and the line looks like a world name
        if current_bucket is not None and _WORLD_NAME_RE.fullmatch(ln):
            current_bucket.append(ln)

    notice_dt = parse_notice_date(notice)
    return notice_dt, new_world, preferred, standard, congested


###################
# End GPT Section #
###################


def _add_world_event(
    world_history: Dict[str, list],
    date: datetime.date,
    status: WorldStatus,
    name: str,
):
    world_history.setdefault(name, []).append((status, date))


def init_world_status(
    world_creation_path: Path = WORLD_CREATION_PATH,
) -> Dict[str, list]:
    """Initialize world status with an initial event for every world."""
    world_creation = {}

    with open(world_creation_path, "r") as inf:
        wc_data = inf.readlines()
        wc_data = filter(lambda x: x.strip()[0] != "#", wc_data)

    for line in wc_data:
        parts = line.split()
        name = parts[1]
        date_str = " ".join(parts[2:5])
        date_obj = datetime.datetime.strptime(date_str, "%B %d, %Y").date()
        world_creation[name] = date_obj

    world_history: Dict[str, list] = {}
    for name in world_creation:
        world_history[name] = []
        if world_creation[name] < WPBI_INTRODUCED:
            world_history[name].append((WorldStatus.PRE_WPBI, world_creation[name]))
        else:
            # Assumes that every world created after the start of WPBI is NEW,
            # which is true for now and seems like it should be true generally
            world_history[name].append((WorldStatus.NEW, world_creation[name]))

    return world_history


def update_worlds_nonstandard_notices(world_history: Dict[str, list]):
    # Several world status changes are done in a non-standard format prior to the
    # introduction of the standardized world status change notification on
    # 2017-07-18. Two of these are given in "Topics" on the Lodestone as opposed to
    # "Notices", while one is given in a non-standard notice format. Instead of
    # scraping and parsing all these formats, I'm going to manually put in the updates
    # here while linking to their announcement pages. I can't guarantee that I have
    # found all world status changes, so the data in the first two months (between
    # the introduction on May 17 and the first standard notice on July 18) may be
    # a little dubious.

    # The initial introduction of the WPBI system marks several worlds as congested
    # https://na.finalfantasyxiv.com/lodestone/topics/detail/fee198ff2f37cd22f5b138f7672360440abe9651
    WPBI_CONGESTED = [
        "Bahamut",
        "Chocobo",
        "Mandragora",
        "Shinryu",
        "Balmung",
        "Gilgamesh",
    ]
    for name in WPBI_CONGESTED:
        _add_world_event(world_history, WPBI_INTRODUCED, WorldStatus.CONGESTED, name)

    # Carbuncle is separately marked as congested when the new world incentives
    # are introduced in a topics post on June 14/15
    # https://na.finalfantasyxiv.com/lodestone/topics/detail/5e1a319accdb6ec98b54ef82e35d22338cf55ce7
    _add_world_event(
        world_history, datetime.date(2017, 6, 15), WorldStatus.CONGESTED, "Carbuncle"
    )

    # A non-standard notice adds congested worlds on 2017-06-19
    # https://na.finalfantasyxiv.com/lodestone/news/detail/7ed4e90df2adf74056abb61fa2951ef5730f42e6
    _add_world_event(
        world_history, datetime.date(2017, 6, 19), WorldStatus.CONGESTED, "Tonberry"
    )
    _add_world_event(
        world_history, datetime.date(2017, 6, 19), WorldStatus.CONGESTED, "Odin"
    )
    _add_world_event(
        world_history, datetime.date(2017, 6, 19), WorldStatus.CONGESTED, "Cerberus"
    )


def update_worlds_from_notices(world_history: Dict[str, list], notices: list):
    """Updates world histories with a list of standard notices from the website.
    Assumes that all notices fed into the function use the standard world update
    format (the filtered output from the notice scraper)."""
    # Sort notices from earliest to latest (mostly reverses the order from input)
    notices = sorted(notices, key=parse_notice_date)

    for notice in notices:
        n_date, n_new, n_pref, n_stand, n_cong = extract_world_changes(notice)
        for name in n_new:
            _add_world_event(world_history, n_date, WorldStatus.NEW, name)

        for name in n_pref:
            _add_world_event(world_history, n_date, WorldStatus.PREFERRED, name)

        for name in n_stand:
            _add_world_event(world_history, n_date, WorldStatus.STANDARD, name)

        for name in n_cong:
            _add_world_event(world_history, n_date, WorldStatus.CONGESTED, name)


def sancheck_world_history(world_history: Dict[str, list]):
    def sancheck_history(hist):
        cur_status = None
        cur_date = datetime.date(1900, 1, 1)
        for stat, d in hist:
            assert d > cur_date
            assert stat != cur_status
            cur_status = stat
            cur_date = d

    for name in world_history:
        try:
            sancheck_history(world_history[name])
        except Exception as e:
            print(f"!!!! Sanity Check Failed for {name} !!!!")
            for statchange in world_history[name]:
                print(statchange)
            raise (e)


def get_world_history_all(
    notices: list,
    world_creation_path: Path = WORLD_CREATION_PATH,
) -> Dict[str, list]:
    """The main driver function. Takes a list of JSON notices scraped from
    the Lodestone (which must all pertain to World Status Changes) and
    produces a history for each world."""

    histories = init_world_status(world_creation_path)
    update_worlds_nonstandard_notices(histories)
    update_worlds_from_notices(histories, notices)
    sancheck_world_history(histories)

    return histories


def serialize_world_history(world_history: Dict[str, list]) -> List[dict]:
    """Convert the world history dict to a list of JSON-serializable records."""
    records = []
    for name, history in world_history.items():
        events = [
            {"status": status.name, "date": date.isoformat()}
            for status, date in history
        ]
        records.append({"world": name, "history": events})
    return records


def main():
    print(FILE_DIR.parent)
    ap = argparse.ArgumentParser(
        description="Build FFXIV world status histories from scraped notices."
    )
    ap.add_argument(
        "--status-notices",
        type=Path,
        default=FILE_DIR.parent / "data" / "status_notices.jsonl",
        help="JSONL file of filtered world status notices (output of scrape_notices.py).",
    )
    ap.add_argument(
        "--world-creation",
        type=Path,
        default=WORLD_CREATION_PATH,
        help="Path to world_creation.txt.",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=FILE_DIR.parent / "data" / "world_history.jsonl",
        help="Output JSONL file for the world history (one world per line).",
    )
    args = ap.parse_args()

    with open(args.status_notices, "r") as f:
        notices = [json.loads(line) for line in f]

    histories = get_world_history_all(notices, args.world_creation)

    records = serialize_world_history(histories)
    with open(args.output, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
