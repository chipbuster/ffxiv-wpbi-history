**Disclaimer: The first version of this code was thrown together with ChatGPT
and some hack-job manual coding. The refinements were partially done by hand
with refinements done by Claude Code. It is not optimized for being 
well-structured or understandable.** If you want to modify this, you will
probably need light coding experience, or access to a chatbot.

## More details on tooling

This tool consists of several components:

- A tool to scrape notices from the Lodestone and store the ones that appear to
  correspond to world status changes (`scrape_notices.py`)
- A tool to analyze the scraped notices and create a clean history of world
  status changes, without duplicates (`analyze_world_history.py`)
- A tool to scrape patch dates off of the FFVIX ConsoleGames Wiki (`scrape_patch_dates.py`)
- A tool to create the plots seen in the README using this data (`plot_world_history.py`)

It also contains a driver script (`update_repo.py`) along with some GitHub Actions
which keep the repository up to date.

### Quickstart

This repository uses `uv` to manage dependencies. To get started, install
the dependencies, as well as the browsers that playwright uses to do the
scraping:

```bash
uv sync
uv run playwright install
```

From there, you can run the update script to get the latest information by 
running

```bash
uv run update_repo.py
```

Once you've done this, you can also examine when world status changes occurred
relative to patches, by running `uv run scripts/analyze_patch_dates.py`. 
`update_repo.py` has short explanations of what each script does.

### Data Sources

Most data for world congestion status is found in the form of notices on the
Lodestone. However, in the early days of the system, it seems that congested
worlds were announced via other means. I have manually collected the data from
some of these notices into the script, but I may have missed some, meaning the
data for the first two months after the introduction of the WPBI system may not
be accurate. The first standard notice happens on 2017-07-18.

In addition, the dates for creation of a world are taken from the
[Console Games Wiki](https://ffxiv.consolegameswiki.com/wiki/Servers) and
stored in `world_creation.txt`. Any world which is created before the
congestion system is implemented is given an initial state of `PRE_WPBI` which
just means that it doesn't have a congested status yet. Any world created
after the system is assumed to start off in the `NEW` state.

### Scraper Checking

Scraping datasets like this can be surprisingly difficult. For example,
an initial version of the code checked for the line "Changed to Congested
World" to determine which worlds were being set to Congested. However, this
can actually fail multiple ways:

- [Several notices have a typo where the line is "Changde to Congested World"](https://na.finalfantasyxiv.com/lodestone/news/detail/d6342fa250d71b1d9694824ea1796cd1094b1431)
- [If only one world is changed, the notice may read "Changed to **a** Congested World"](https://na.finalfantasyxiv.com/lodestone/news/detail/6c7d04c3238cede50b04abc4787fe0123aaf6f82)
- We need to correctly detect both "New" and "Preferred+" as the same category, since the name changed in 7.3.

This potentially creates a lot of issues where transitions between different
world states can be missed. To try to address this, I wrote a sanity check
which goes over the final list of changes and checks to make sure that
a world never transitions to the same state (e.g. if a world was Standard,
and then we see a notice that it has been changed to a Standard world, this
indicates that we probably missed a change to congested somewhere) and that
there are no changes that occur on the same day.

This sanity check was instrumental to finding the above issues. However,
this obviously not bulletproof, and errors might still exist in the data.

### Plotting Options

The default functionality of the plotting script is to write one SVG per DC
to the `plots` directory. Additional arguments include limiting the x-axis
to a certain set of dates, changing the worlds plotted (pass `worlds=None`
to plot all worlds on the same plot), and changing the output file name.

## Notes On Naming Conventions

Before 7.3, the ["Preferred+" World status was known as new](https://na.finalfantasyxiv.com/lodestone/news/detail/7f6fa05ecc979911791a6019c3fc430a24b619e6).
Since writing "Preferred+" is really annoying in code (and also because the first
draft of this code was written very shortly after 7.3), the status is internally
known as "new".

"Notices" are the JSON blobs created by the scraper. E.g. all_notices and
status_notices are the JSON blobs associated with Lodestone scrapes. More
refined data are not called notices, e.g. the extracted set of world status
changes are the world_history.
