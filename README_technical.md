## More details on tooling

This tool consists of several components:

- a scraper to gather data from Lodestone (mostly written by ChatGPT because I *hate* writing scraper code)
- a cleanup utility which grabs just the world status changes,
- some code to analyze and validate the world status history and serialize it
- plotting code to visualize the changes (also mostly written by GPT, because I haven't touched matplotlib in a hot decade)

**This code is just something I threw together in an evening and is not
intended to be very user-friendly**. You will need to be at least somewhat
familiar with Python (or be willing to ask a friend/LLM for help) in order
to be able to use this code effectively.

Large portions of the plotting and textual analysis code were written by ChatGPT
in chatbot mode. A number of smaller later revisions were written with Claude
Code.

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
can actually fail for two different reasons:

- [Several notices have a typo where the line is "Changde to Congested World"](https://na.finalfantasyxiv.com/lodestone/news/detail/d6342fa250d71b1d9694824ea1796cd1094b1431)
- [If only one world is changed, the notice may read "Changed to **a** Congested World"](https://na.finalfantasyxiv.com/lodestone/news/detail/6c7d04c3238cede50b04abc4787fe0123aaf6f82)

This potentially creates a lot of issues where transitions between different
world states can be missed. To try to address this, I wrote a sanity check
which goes over the final list of changes and checks to make sure that
a world never transitions to the same state (e.g. if a world was Standard,
and then we see a notice that it has been changed to a Standard world, this
indicates that we probably missed a change to congested somewhere) and that
there are no changes that occur on the same day.

This sanity check was instrumental to finding the above two issues. However,
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
