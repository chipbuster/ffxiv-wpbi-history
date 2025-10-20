import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pickle, datetime
from enum import Enum, auto

WPBI_INTRODUCED = datetime.date(2017, 5, 17)
WORLDVISIT_INTRODUCED = datetime.date(2019, 4, 23)

class WorldStatus(Enum):
    PRE_WPBI = auto()   # Before world population balancing incentives
    NEW = auto()
    PREFERRED = auto()
    STANDARD = auto()
    CONGESTED = auto()

with open("worlds.pkl","rb") as pklf:
    world_history = pickle.load(pklf)

# The plotting code is mostly written by GPT, with some manual human 
# intervention to plot particular dates. The structure here is...kinda awful
# (why are we replicating plotting work in the legend part??) but I can't
# really be bothered to fix it, lest GPT break it all.

# === FFXIV Data Center World Lists ===

aether_worlds = [
    "Adamantoise", "Cactuar", "Faerie", "Gilgamesh",
    "Jenova", "Midgardsormr", "Sargatanas", "Siren"
]

primal_worlds = [
    "Behemoth", "Excalibur", "Exodus", "Famfrit",
    "Hyperion", "Lamia", "Leviathan", "Ultros"
]

crystal_worlds = [
    "Balmung", "Brynhildr", "Coeurl", "Diabolos",
    "Goblin", "Malboro", "Mateus", "Zalera"
]

dynamis_worlds = [
    "Cuchulainn", "Golem", "Halicarnassus", "Kraken",
    "Maduin", "Marilith", "Rafflesia", "Seraph"
]

elemental_worlds = [
    "Aegis", "Atomos", "Carbuncle", "Garuda",
    "Gungnir", "Kujata", "Tonberry", "Typhon"
]

gaia_worlds = [
    "Alexander", "Bahamut", "Durandal", "Fenrir",
    "Ifrit", "Ridill", "Tiamat", "Ultima"
]

mana_worlds = [
    "Anima", "Asura", "Chocobo", "Hades",
    "Ixion", "Masamune", "Pandaemonium", "Titan"
]

meteor_worlds = [
    "Belias", "Mandragora", "Ramuh", "Shinryu",
    "Unicorn", "Valefor", "Yojimbo", "Zeromus"
]

chaos_worlds = [
    "Cerberus", "Louisoix", "Moogle", "Omega",
    "Ragnarok", "Spriggan"
]

light_worlds = [
    "Lich", "Odin", "Phoenix", "Shiva", "Twintania", "Zodiark"
]

materia_worlds = [
    "Bismarck", "Ravana", "Sephirot", "Sophia", "Zurvan"
]

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
    WorldStatus.PRE_WPBI: "#7F7F7F",  # Gray
    WorldStatus.NEW: "#F78DC9",       # Soft magenta/pink
    WorldStatus.PREFERRED: "#55A868", # Green (Okabe-Ito)
    WorldStatus.STANDARD: "#4C72B0",  # Blue (Okabe-Ito)
    WorldStatus.CONGESTED: "#C44E52"  # Red (Okabe-Ito)
}

def plot_world_status_timeline(world_history, **kwargs):
    defaultKwargs = {
            "worlds": list(world_history.keys()),
            "begin_date": datetime.date(2013, 8, 16),
            "end_date": datetime.date.today(),
            "out_file": "plots/output.svg",
            "title": "FFXIV World Status Timeline"
    }
    kwargs = {**defaultKwargs, **kwargs}

    worlds = kwargs["worlds"]
    begin_date = kwargs["begin_date"]
    end_date = kwargs["end_date"]
    out_file = kwargs["out_file"]
    title_str = kwargs["title"]

    worlds.sort(reverse=True)

    fig, ax = plt.subplots(figsize=(12, max(6, len(worlds) * 0.3)))

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
                linewidth=8
            )
        # Last segment runs to "today" for visualization or to next known marker
        last_status, last_date = history[-1]
        ax.hlines(
            y=y_positions[world],
            xmin=mdates.date2num(last_date),
            xmax=mdates.date2num(datetime.date.today()),
            colors=STATUS_COLORS[last_status],
            linewidth=8,
        )

    ax.axvline(
        x=mdates.date2num(WPBI_INTRODUCED),
        color="black",
        linestyle="--",
        linewidth=1.5,
        alpha=0.8,
        label="World Population Balancing Introduced"
    )

    ax.axvline(
        x=mdates.date2num(WORLDVISIT_INTRODUCED),
        color="black",
        linestyle=":",
        linewidth=1.5,
        alpha=0.8,
        label="World Visit System Introduced"
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

    ax.set_xlabel("Date")
    ax.set_title(title_str)
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center")

    # Legend
    handles = [
        plt.Line2D([0], [0], color=color, lw=6, label=status.name)
        for status, color in STATUS_COLORS.items()] +\
    [plt.Line2D([0], [0], color="#333333", linestyle="--", label="WPBI system begins")]+\
    [plt.Line2D([0], [0], color="#333333", linestyle=":", label="World Visit begins")]

    ax.legend(handles=handles, title="Status", bbox_to_anchor=(1.04, 1), loc="upper left")

    plt.tight_layout()
    plt.savefig(out_file)

for dc in ffxiv_data_centers:
    plot_world_status_timeline(world_history, worlds=ffxiv_data_centers[dc], out_file=f"plots/{dc}.svg", title=f"History of Worlds on {dc}")
    plot_world_status_timeline(world_history, worlds=ffxiv_data_centers[dc], out_file=f"prev_year/{dc}.svg", title=f"History of Worlds on {dc}", begin_date = datetime.date.today() - datetime.timedelta(days=540))

# An example call which plots all worlds in a limited timeframe
# plot_world_status_timeline(world_history, begin_date = datetime.date(2020, 1, 1), end_date = datetime.date(2024, 1, 1))
