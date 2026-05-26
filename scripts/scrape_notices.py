# scrape_lodestone_notices.py (fixed: detail in second tab; robust pagination)
import argparse
import asyncio
import datetime
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.async_api import async_playwright

CATEGORY_URL = "https://na.finalfantasyxiv.com/lodestone/news/category/1"
LOG = logging.getLogger("lodestone")
WBPI_FILTER_PHRASE = "Congested/Preferred".lower()


def setup_logging(level: str):
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


WS = re.compile(r"[ \t\r\f\v]+")


def normalize_text(x: str) -> str:
    lines = [WS.sub(" ", ln).strip() for ln in x.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def parse_notice_date(notice):
    fmt_candidates = ["%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y", "%Y-%m-%d"]
    if "date" in notice and notice["date"]:
        for fmt in fmt_candidates:
            try:
                return datetime.datetime.strptime(notice["date"], fmt).date()
            except Exception:
                pass
    raise ValueError("Could not parse date from notice.")


async def click_through_unsupported(page):
    if "/error/unsupported_browser/" in page.url:
        LOG.info(
            "Unsupported browser interstitial detected; attempting to click through."
        )
        try:
            if await page.get_by_text("Display Site", exact=True).count():
                await page.get_by_text("Display Site", exact=True).first.click()
                await page.wait_for_load_state("domcontentloaded")
                LOG.debug("Clicked 'Display Site'.")
            if await page.get_by_text("Confirm").count():
                yes_btn = page.get_by_role(
                    "button", name=re.compile(r"^\s*Yes\s*$", re.I)
                )
                if await yes_btn.count():
                    await yes_btn.first.click()
                    LOG.debug("Confirmed 'Yes' on dialog.")
                else:
                    await page.get_by_role("button").first.click()
                await page.wait_for_load_state("domcontentloaded")
        except Exception as e:
            LOG.warning("Interstitial bypass attempt encountered an error: %s", e)


async def extract_list_links(list_page) -> List[str]:
    selectors = [
        "ul.news__list a",
        ".news__list a",
        "div.ldst__main a",
        "a:has(h3), a:has(p)",
    ]
    hrefs = []
    for sel in selectors:
        anchors = await list_page.locator(sel).element_handles()
        for a in anchors:
            href = await a.get_attribute("href")
            if not href:
                continue
            if not href.startswith("http"):
                href = list_page.url.split("/lodestone/")[0] + href
            if "/lodestone/news/detail/" in href:
                hrefs.append(href)
    # de-dup preserve order
    seen, out = set(), []
    for h in hrefs:
        if h not in seen:
            seen.add(h)
            out.append(h)
    LOG.info("Found %d detail links on page.", len(out))
    return out


async def extract_detail(detail_page, url: str) -> Optional[Dict]:
    LOG.info("Crawling detail: %s", url)
    await detail_page.goto(url, wait_until="domcontentloaded")
    await click_through_unsupported(detail_page)

    title = ""
    for sel in ["h1", "h2", "header h1", "article h1", ".news__detail__title"]:
        els = detail_page.locator(sel)
        if await els.count():
            title = (await els.first.inner_text()).strip()
            break

    date_text, category = "", "Notices"
    for sel in [
        ".news__header",
        ".news__meta",
        ".ldst__content",
        "article header",
        ".news__detail__header",
    ]:
        loc = detail_page.locator(sel)
        if await loc.count():
            txt = normalize_text(await loc.first.inner_text())
            m = re.search(r"(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})", txt)
            if m and not date_text:
                date_text = m.group(1)
            if "Notices" in txt:
                category = "Notices"
            break

    body = ""
    for sel in [
        ".news__detail__inner",
        ".news__detail__body",
        "article .news__detail",
        "article",
        ".ldst__content",
    ]:
        loc = detail_page.locator(sel)
        if await loc.count():
            body = normalize_text(await loc.first.inner_text())
            if len(body) > 100:
                break

    if not title and not body:
        LOG.warning("No content extracted: %s", url)
        return None

    LOG.debug("Extracted title len=%d, body len=%d", len(title), len(body))
    return {
        "url": url,
        "title": title,
        "date": date_text,
        "category": category,
        "body": body,
    }


def _bump_page_param(listing_url: str) -> str:
    """Increment ?page=N (or add ?page=2) on the *listing* URL, preserving other params/fragments."""
    parsed = urlparse(listing_url)
    qs = parse_qs(parsed.query)
    try:
        n = int(qs.get("page", ["1"])[0])
        qs["page"] = [str(n + 1)]
    except Exception:
        qs["page"] = ["2"]
    new_q = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_q))


async def find_next_page(list_page, current_listing_url: str) -> Optional[str]:
    """Find the next category page; choose the smallest page number > current.
    If no anchors, synthesize ?page=current+1 on the *listing* URL."""
    # 1) Try explicit "next" anchors first
    candidates = [
        "a[rel='next']",
        "a:has-text('Next')",
        "li.pagination__next a",
        ".pagination a:has-text('>')",
        "nav.pagination a.next, nav.pager a.next, .btn__pager__next a, li.next a",
        "ul.pagination li.next a, ul.btn__pager li.btn__pager__next a",
    ]
    for sel in candidates:
        loc = list_page.locator(sel)
        if await loc.count():
            href = await loc.first.get_attribute("href")
            if href:
                if not href.startswith("http"):
                    href = current_listing_url.split("/lodestone/")[0] + href
                LOG.info("Next page via anchor: %s", href)
                return href

    # 2) Numeric fallback: pick the *smallest* N > current
    try:
        curr_page_num = int(re.search(r"[?&]page=(\d+)", current_listing_url).group(1))
    except Exception:
        curr_page_num = 1

    links = await list_page.locator("a[href*='page=']").element_handles()
    candidates_ns = []
    for a in links:
        href = await a.get_attribute("href")
        if not href:
            continue
        m = re.search(r"[?&]page=(\d+)", href)
        if m:
            n = int(m.group(1))
            if n > curr_page_num:
                candidates_ns.append((n, href))

    if candidates_ns:
        # Choose the nearest next page, not the largest
        n_next, href = min(candidates_ns, key=lambda t: t[0])
        if not href.startswith("http"):
            href = current_listing_url.split("/lodestone/")[0] + href
        LOG.info(
            "Next page via numeric link: current=%d -> next=%d (%s)",
            curr_page_num,
            n_next,
            href,
        )
        return href

    # 3) Last resort: synthesize current+1
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    parsed = urlparse(current_listing_url)
    qs = parse_qs(parsed.query)
    qs["page"] = [str(curr_page_num + 1)]
    bumped = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
    LOG.info(
        "No next link found; synthesizing: current=%d -> next=%d (%s)",
        curr_page_num,
        curr_page_num + 1,
        bumped,
    )
    return bumped


async def scrape(
    category_url: str,
    cutoff_date: datetime.date,
    per_item_delay: float,
):
    results: List[Dict] = []
    t0 = time.time()

    # We want to allow for the fact that a few posts on the lodestone may be
    # out-of-order. For this, we say that we need to see four pages older
    # than the cutoff date in order to bail out of scraping.
    MAX_PAGES_OVER_CUTOFF_DATE = 4
    num_pages_over_cutoff_date = 0

    LOG.info(
        "Starting scrape: %s (max_pages=%s, per_item_delay=%.2fs)",
        category_url,
        max_pages,
        per_item_delay,
    )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
        )

        # Keep one page for the listing, and a second for details
        list_page = await context.new_page()
        detail_page = await context.new_page()

        page_url = category_url
        page_count = 0
        empty_pages_in_a_row = 0

        while page_url and (max_pages is None or page_count < max_pages):
            LOG.info("Opening category page %d: %s", page_count + 1, page_url)
            await list_page.goto(page_url, wait_until="domcontentloaded")
            await click_through_unsupported(list_page)
            current_listing_url = list_page.url  # always a listing URL

            links = await extract_list_links(list_page)
            LOG.info(
                "Processing %d detail links from page %d.", len(links), page_count + 1
            )

            if not links:
                empty_pages_in_a_row += 1
                if empty_pages_in_a_row >= 2:
                    LOG.info("Two consecutive empty pages; stopping pagination.")
                    break
            else:
                empty_pages_in_a_row = 0

            for href in links:
                if per_item_delay > 0:
                    LOG.debug(
                        "Sleeping for %.2fs to respect rate limit.", per_item_delay
                    )
                    await asyncio.sleep(per_item_delay)
                detail = await extract_detail(detail_page, href)
                if detail:
                    results.append(detail)
                    if jsonl_path:
                        with jsonl_path.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(detail, ensure_ascii=False) + "\n")
                    try:
                        notice_date = parse_notice_date(detail)
                        if notice_date < cutoff_date:
                            num_pages_over_cutoff_date += 1
                    except Exception as e:
                        LOG.info(f"Could not extract notice date from URL {href}")

                else:
                    LOG.warning("Skipped detail due to empty extraction: %s", href)

            if num_pages_over_cutoff_date < MAX_PAGES_OVER_CUTOFF_DATE:
                next_url = await find_next_page(list_page, current_listing_url)
                if not next_url:
                    LOG.info("Stopping: no further pages.")
                    break
                LOG.info("Navigating to next category page: %s", next_url)
                await asyncio.sleep(0.5)
                page_url = next_url
            else:
                LOG.info(
                    f"Found {num_pages_over_cutoff_date} pages older than {cutoff_date}, stopping now",
                )
                break

        await context.close()
        await browser.close()

    LOG.info(
        "Done. Extracted %d details across %d category page(s) in %.1fs.",
        len(results),
        page_count,
        time.time() - t0,
    )
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cutoff-date",
        type=lambda s: datetime.date.fromisoformat(s),
        default=datetime.date(2000, 1, 1),
    )
    ap.add_argument(
        "--all-notices",
        type=Path,
        default=None,
        help="Write a JSONL containing all scraped notices to this path.",
    )
    ap.add_argument(
        "--wpbi-notices",
        type=Path,
        default=None,
        help="Write a JSONL containing notices that mention WPBI to this path.",
    )
    ap.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Seconds between detail page fetches (default 0.4).",
    )
    ap.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level: DEBUG, INFO, WARNING, ERROR.",
    )
    args = ap.parse_args()

    setup_logging(args.log_level)

    results = asyncio.run(
        scrape(
            category_url=CATEGORY_URL,
            cutoff_date=args.cutoff_date,
            per_item_delay=args.delay,
        )
    )

    if results and args.all_notices:
        with open(args.all_notices, "w") as res_f:
            for res in results:
                res_f.write(json.dumps(res) + "\n")

    if results and args.wpbi_notices:
        # The outputs might be duplicated, so we deduplicate them by URL.
        output_idxs = set()
        output_urls = set()

        for i, res in enumerate(results):
            if WBPI_FILTER_PHRASE in res["body"].lower() and res["url"] not in urls:
                output_urls.add(res["url"])
                output_idxs.add(i)

        wbpi_res = [results[i] for i in output_idxs]
        wbpi_res.sort(key=parse_notice_date)

        with open(args.wbpi_notices, "w") as res_f:
            for res in wbpi_res:
                res_f.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()
