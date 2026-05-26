import argparse
import datetime
import json
import os
from enum import Enum, auto
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

WPBI_INTRODUCED = datetime.date(2017, 5, 17)
WORLDVISIT_INTRODUCED = datetime.date(2019, 4, 23)

FILE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WORLD_HISTORY_PATH = FILE_DIR.parent / "data" / "world_history.jsonl"


class WorldStatus(Enum):
    PRE_WPBI = auto()  # Before world population balancing incentives
    NEW = auto()
    PREFERRED = auto()
    STANDARD = auto()
    CONGESTED = auto()


def load_world_history(path: Path) -> dict:
    world_history = {}
    with open(path, "r") as f:
        for line in f:
            record = json.loads(line)
            world_history[record["world"]] = [
                (
                    WorldStatus[event["status"]],
                    datetime.date.fromisoformat(event["date"]),
                )
                for event in record["history"]
            ]
    return world_history


# The plotting code is mostly written by GPT, with some manual human
# intervention to plot particular dates. The structure here is...kinda awful
# (why are we replicating plotting work in the legend part??) but I can't
# really be bothered to fix it, lest GPT break it all.

# === FFXIV Data Center World Lists ===

aether_worlds = [
    "Adamantoise",
    "Cactuar",
    "Faerie",
    "Gilgamesh",
    "Jenova",
    "Midgardsormr",
    "Sargatanas",
    "Siren",
]

primal_worlds = [
    "Behemoth",
    "Excalibur",
    "Exodus",
    "Famfrit",
    "Hyperion",
    "Lamia",
    "Leviathan",
    "Ultros",
]

crystal_worlds = [
    "Balmung",
    "Brynhildr",
    "Coeurl",
    "Diabolos",
    "Goblin",
    "Malboro",
    "Mateus",
    "Zalera",
]

dynamis_worlds = [
    "Cuchulainn",
    "Golem",
    "Halicarnassus",
    "Kraken",
    "Maduin",
    "Marilith",
    "Rafflesia",
    "Seraph",
]

elemental_worlds = [
    "Aegis",
    "Atomos",
    "Carbuncle",
    "Garuda",
    "Gungnir",
    "Kujata",
    "Tonberry",
    "Typhon",
]

gaia_worlds = [
    "Alexander",
    "Bahamut",
    "Durandal",
    "Fenrir",
    "Ifrit",
    "Ridill",
    "Tiamat",
    "Ultima",
]

mana_worlds = [
    "Anima",
    "Asura",
    "Chocobo",
    "Hades",
    "Ixion",
    "Masamune",
    "Pandaemonium",
    "Titan",
]

meteor_worlds = [
    "Belias",
    "Mandragora",
    "Ramuh",
    "Shinryu",
    "Unicorn",
    "Valefor",
    "Yojimbo",
    "Zeromus",
]

chaos_worlds = ["Cerberus", "Louisoix", "Moogle", "Omega", "Ragnarok", "Spriggan"]

light_worlds = ["Lich", "Odin", "Phoenix", "Shiva", "Twintania", "Zodiark"]

materia_worlds = ["Bismarck", "Ravana", "Sephirot", "Sophia", "Zurvan"]

ffxiv_data_centers = {
    "Aether": aether_worlds,
    "Primal": primal_worlds,
    "Crystal": crystal_worlds,
    "Dynamis": dynamis_worlds,
    "Elemental": elemental_worlds,
    "Gaia": gaia_worlds,
    "Mana": mana_worlds,
    "Meteor": meteor_worlds,
    "Chaos": chaos_worlds,
    "Light": light_worlds,
    "Materia": materia_worlds,
}

# Colorblind-friendly palette approximating your request
STATUS_COLORS = {
    WorldStatus.PRE_WPBI: "#7A8FA6",  # Slate blue-gray
    WorldStatus.NEW: "#AB47BC",        # Vibrant purple
    WorldStatus.PREFERRED: "#2ECC71",  # Emerald green
    WorldStatus.STANDARD: "#2196F3",   # Vivid blue
    WorldStatus.CONGESTED: "#E53935",  # Bright red
}

STATUS_LABELS = {
    WorldStatus.PRE_WPBI: "Pre-Balancing",
    WorldStatus.NEW: "Preferred+",
    WorldStatus.PREFERRED: "Preferred",
    WorldStatus.STANDARD: "Standard",
    WorldStatus.CONGESTED: "Congested",
}


def plot_world_status_timeline(world_history, **kwargs):
    defaultKwargs = {
        "worlds": list(world_history.keys()),
        "begin_date": datetime.date(2013, 8, 16),
        "end_date": datetime.date.today(),
        "out_file": "plots/output.svg",
        "title": "FFXIV World Status Timeline",
    }
    kwargs = {**defaultKwargs, **kwargs}

    worlds = kwargs["worlds"]
    begin_date = kwargs["begin_date"]
    end_date = kwargs["end_date"]
    out_file = kwargs["out_file"]
    title_str = kwargs["title"]

    worlds.sort(reverse=True)

    fig, ax = plt.subplots(figsize=(12, len(worlds) * 4 / 6))

    # Sort worlds alphabetically for consistent y positions
    y_positions = {world: i for i, world in enumerate(worlds)}

    for world in worlds:
        history = world_history[world]
        # Ensure transitions are sorted by date
        history = sorted(history, key=lambda x: x[1])

        # Go through each consecutive pair
        for (status, start_date), (next_status, next_date) in zip(history, history[1:]):
            ax.hlines(
                y=y_positions[world],
                xmin=mdates.date2num(start_date),
                xmax=mdates.date2num(next_date),
                colors=STATUS_COLORS[status],
                linewidth=20,
                capstyle="butt",
            )
        # Last segment runs to "today" for visualization or to next known marker
        last_status, last_date = history[-1]
        ax.hlines(
            y=y_positions[world],
            xmin=mdates.date2num(last_date),
            xmax=mdates.date2num(datetime.date.today()),
            colors=STATUS_COLORS[last_status],
            linewidth=20,
            capstyle="butt",
        )

    ax.set_ylim(-0.5, len(worlds) - 0.5)

    show_wpbi = begin_date <= WPBI_INTRODUCED <= end_date
    show_worldvisit = begin_date <= WORLDVISIT_INTRODUCED <= end_date

    if show_wpbi:
        ax.axvline(
            x=mdates.date2num(WPBI_INTRODUCED),
            color="black",
            linestyle="--",
            linewidth=1.5,
            alpha=0.8,
        )

    if show_worldvisit:
        ax.axvline(
            x=mdates.date2num(WORLDVISIT_INTRODUCED),
            color="black",
            linestyle=":",
            linewidth=1.5,
            alpha=0.8,
        )

    # Format axis
    ax.set_yticks(list(y_positions.values()))
    ax.set_yticklabels(worlds)

    print(f"{begin_date} -- {end_date}")
    ax.set_xlim(mdates.date2num(begin_date), mdates.date2num(end_date))

    #    year_locator = mdates.MonthLocator()  # defaults to every 1 year
    #    year_fmt = mdates.DateFormatter("%Y-%m")
    #    ax.xaxis.set_major_locator(year_locator)
    #    ax.xaxis.set_major_formatter(year_fmt)

    loc = mdates.AutoDateLocator(minticks=12, maxticks=20)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))

    ax.grid(axis="x", color="black", alpha=0.08, linewidth=0.7, zorder=0)

    ax.set_xlabel("Date")
    ax.set_title(title_str, fontsize=16, fontfamily="serif")
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center")

    # Legend
    handles = (
        [
            plt.Line2D([0], [0], color=color, lw=6, label=STATUS_LABELS[status])
            for status, color in STATUS_COLORS.items()
        ]
        + (
            [plt.Line2D([0], [0], color="#333333", linestyle="--", label="WPBI system begins")]
            if show_wpbi else []
        )
        + (
            [plt.Line2D([0], [0], color="#333333", linestyle=":", label="World Visit begins")]
            if show_worldvisit else []
        )
    )

    ax.legend(
        handles=handles, title="Status", bbox_to_anchor=(1.04, 0.5), loc="center left"
    )

    plt.tight_layout()
    plt.savefig(out_file)


def _default_begin_date() -> datetime.date:
    today = datetime.date.today()
    try:
        return today.replace(year=today.year - 2)
    except ValueError:
        return today.replace(year=today.year - 2, day=28)


def _parse_history_length(s: str) -> datetime.date:
    if s.lower() == "all":
        return datetime.date(2017, 1, 1)
    return datetime.date.fromisoformat(s)


def main():
    ap = argparse.ArgumentParser(
        description="Plot FFXIV world status timelines by data center."
    )
    ap.add_argument(
        "--world-history",
        type=Path,
        default=WORLD_HISTORY_PATH,
        help=f"World history JSONL produced by analyze_world_history.py (default: {WORLD_HISTORY_PATH})",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=FILE_DIR.parent / "plots",
        help="Directory to write SVG plots into (default: <project>/plots).",
    )
    ap.add_argument(
        "--history-length",
        type=_parse_history_length,
        default=_default_begin_date(),
        metavar="DATE",
        help="Earliest date to include in plots, as YYYY-MM-DD (default: 24 months ago).",
    )
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    wh = load_world_history(args.world_history)

    for dc, worlds in ffxiv_data_centers.items():
        plot_world_status_timeline(
            wh,
            worlds=worlds,
            out_file=args.output_dir / f"{dc}.svg",
            title=dc,
            begin_date=args.history_length,
        )


if __name__ == "__main__":
    main()
