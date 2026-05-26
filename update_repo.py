# This script updates the data in the repository by running all of the other
# scripts we need. We prefer explicit flag passing instead of relying on
# defaults.
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
ALL_NOTICES_FILE = REPO_ROOT / "data" / "all_notices.jsonl"
STATUS_NOTICES_FILE = REPO_ROOT / "data" / "status_notices.jsonl"
WORLD_HISTORY_FILE = REPO_ROOT / "data" / "world_history.jsonl"
WORLD_CREATION_FILE = REPO_ROOT / "data" / "world_creation.txt"  # Not a JSON!
PATCH_HISTORY_FILE = REPO_ROOT / "data" / "patch_dates.jsonl"

PLOT_ALL_TIME_DIR = REPO_ROOT / "plots" / "all_time"
PLOT_LIMITED_DIR = REPO_ROOT / "plots" / "lim_time"

# Step 1: Update all_notices.jsonl and status_notices.jsonl with the update flag.
scrape_script = REPO_ROOT / "scripts" / "scrape_notices.py"
subprocess.run(
    [
        "uv",
        "run",
        scrape_script,
        "--update",
        "--all-notices",
        ALL_NOTICES_FILE,
        "--status-notices",
        STATUS_NOTICES_FILE,
    ]
)

# Step 2: Scrape a list of patch dates from the wiki, relying on the default
# values for the URL
patch_script = REPO_ROOT / "scripts" / "scrape_patch_dates.py"
subprocess.run(["uv", "run", patch_script, "--patch-dates", PATCH_HISTORY_FILE])

# Step 3: Create the refined world history file, which just contains world
# status changes and dates for each world.
analysis_script = REPO_ROOT / "scripts" / "analyze_world_history.py"
subprocess.run(
    [
        "uv",
        "run",
        analysis_script,
        "--world-creation",
        WORLD_CREATION_FILE,
        "--status-notices",
        STATUS_NOTICES_FILE,
        "--output",
        WORLD_HISTORY_FILE,
    ]
)

# Step 4: Run plotting for both all time and limited
plot_script = REPO_ROOT / "scripts" / "plot_world_history.py"

# Plot all times
subprocess.run(
    [
        "uv",
        "run",
        plot_script,
        "--world-history",
        WORLD_HISTORY_FILE,
        "--output-dir",
        PLOT_ALL_TIME_DIR,
        "--history-length",
        "all",
    ]
)

# Plot default limited history
subprocess.run(
    [
        "uv",
        "run",
        plot_script,
        "--world-history",
        WORLD_HISTORY_FILE,
        "--output-dir",
        PLOT_LIMITED_DIR,
    ]
)

# Optional: run the analysis for patch dates
run_pda = False
if run_pda:
    pda_script = REPO_ROOT / "scripts" / "analyze_patch_dates.py"
    subprocess.run(
        [
            "uv",
            "run",
            pda_script,
            "--patch-dates",
            PATCH_HISTORY_FILE,
            "--world-history",
            WORLD_HISTORY_FILE,
        ]
    )
