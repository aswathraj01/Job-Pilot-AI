"""
scraper.py  —  Scrape job listings from LinkedIn, Indeed, RemoteOK
Uses Playwright for JS-rendered pages, requests+BS4 for static pages.
"""
import hashlib
import time
import random
import requests
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _job_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def _sleep(lo=2.0, hi=5.0):
    time.sleep(random.uniform(lo, hi))


# ── LinkedIn ──────────────────────────────────────────────────────────────────

def scrape_linkedin(config: dict) -> list[dict]:
    if not config.get("linkedin", {}).get("enabled"):
        return []

    cfg = config["linkedin"]
    search = config["job_search"]
    keywords = " ".join(search.get("keywords", ["Software Engineer"]))
    location = search.get("location", "Remote")
    easy_apply = "&f_LF=f_AL" if cfg.get("easy_apply_only", True) else ""

    url = (
        f"https://www.linkedin.com/jobs/search/?"
        f"keywords={requests.utils.quote(keywords)}"
        f"&location={requests.utils.quote(location)}"
        f"&f_WT=2"          # remote filter
        f"{easy_apply}"
        f"&sortBy=DD"        # most recent
    )

    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()

        try:
            # Login
            page.goto("https://www.linkedin.com/login", timeout=30000)
            _sleep(1, 2)
            page.fill("#username", cfg["email"])
            page.fill("#password", cfg["password"])
            page.click("[data-litms-control-urn='login-submit']")
            page.wait_for_load_state("networkidle", timeout=15000)
            _sleep(2, 4)

            # Search
            page.goto(url, timeout=30000)
            page.wait_for_selector(".jobs-search__results-list, .scaffold-layout__list", timeout=15000)
            _sleep(2, 3)

            cards = page.query_selector_all(".job-card-container, .jobs-search-results__list-item")
            logger.info(f"LinkedIn: found {len(cards)} cards")

            for card in cards[:20]:
                try:
                    title_el = card.query_selector(".job-card-list__title, .job-card-container__link")
                    company_el = card.query_selector(".job-card-container__company-name, .artdeco-entity-lockup__subtitle")
                    location_el = card.query_selector(".job-card-container__metadata-item, .artdeco-entity-lockup__caption")
                    link_el = card.query_selector("a[href*='/jobs/view/']")

                    if not title_el or not link_el:
                        continue

                    job_url = "https://www.linkedin.com" + link_el.get_attribute("href").split("?")[0]
                    job = {
                        "id": _job_id(job_url),
                        "title": title_el.inner_text().strip(),
                        "company": company_el.inner_text().strip() if company_el else "",
                        "location": location_el.inner_text().strip() if location_el else location,
                        "url": job_url,
                        "source": "linkedin",
                        "description": "",
                        "match_score": 0,
                        "keywords": [],
                    }
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"LinkedIn card parse error: {e}")
                    continue

            # Fetch descriptions for the first 10
            for job in jobs[:10]:
                try:
                    page.goto(job["url"], timeout=20000)
                    page.wait_for_selector(".jobs-description, .description__text", timeout=10000)
                    _sleep(1, 2)
                    desc_el = page.query_selector(".jobs-description-content__text, .description__text")
                    if desc_el:
                        job["description"] = desc_el.inner_text().strip()[:4000]
                except Exception as e:
                    logger.debug(f"LinkedIn desc fetch error for {job['url']}: {e}")

        except PWTimeout:
            logger.warning("LinkedIn scrape timed out")
        except Exception as e:
            logger.error(f"LinkedIn scrape error: {e}")
        finally:
            browser.close()

    logger.info(f"LinkedIn: returning {len(jobs)} jobs")
    return jobs


# ── Indeed ────────────────────────────────────────────────────────────────────

def scrape_indeed(config: dict) -> list[dict]:
    if not config.get("indeed", {}).get("enabled"):
        return []

    search = config["job_search"]
    keywords = "+".join(search.get("keywords", ["Software Engineer"]))
    location = search.get("location", "Remote")

    url = (
        f"https://www.indeed.com/jobs?"
        f"q={requests.utils.quote(keywords)}"
        f"&l={requests.utils.quote(location)}"
        f"&sort=date"
    )

    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()
        try:
            page.goto(url, timeout=30000)
            page.wait_for_selector("[data-testid='slider_container'], .jobsearch-ResultsList", timeout=15000)
            _sleep(2, 3)

            cards = page.query_selector_all("[data-testid='slider_container'], .job_seen_beacon")
            logger.info(f"Indeed: found {len(cards)} cards")

            for card in cards[:20]:
                try:
                    title_el  = card.query_selector("[data-testid='jobTitle'] a, h2.jobTitle a")
                    company_el = card.query_selector("[data-testid='company-name'], .companyName")
                    loc_el    = card.query_selector("[data-testid='text-location'], .companyLocation")

                    if not title_el:
                        continue

                    href = title_el.get_attribute("href") or ""
                    job_url = "https://www.indeed.com" + href if href.startswith("/") else href
                    job = {
                        "id": _job_id(job_url),
                        "title": title_el.inner_text().strip(),
                        "company": company_el.inner_text().strip() if company_el else "",
                        "location": loc_el.inner_text().strip() if loc_el else location,
                        "url": job_url,
                        "source": "indeed",
                        "description": "",
                        "match_score": 0,
                        "keywords": [],
                    }
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"Indeed card error: {e}")

            for job in jobs[:10]:
                try:
                    page.goto(job["url"], timeout=20000)
                    page.wait_for_selector("#jobDescriptionText, .jobsearch-jobDescriptionText", timeout=10000)
                    _sleep(1, 2)
                    desc_el = page.query_selector("#jobDescriptionText, .jobsearch-jobDescriptionText")
                    if desc_el:
                        job["description"] = desc_el.inner_text().strip()[:4000]
                except Exception as e:
                    logger.debug(f"Indeed desc error: {e}")

        except Exception as e:
            logger.error(f"Indeed scrape error: {e}")
        finally:
            browser.close()

    logger.info(f"Indeed: returning {len(jobs)} jobs")
    return jobs


# ── RemoteOK (public API) ─────────────────────────────────────────────────────

def scrape_remoteok(config: dict) -> list[dict]:
    if not config.get("remoteok", {}).get("enabled", True):
        return []

    keywords = config["job_search"].get("keywords", [])
    kw_lower = [k.lower() for k in keywords]

    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=15,
        )
        data = resp.json()
        if isinstance(data, list):
            data = data[1:]  # first item is metadata
    except Exception as e:
        logger.error(f"RemoteOK fetch error: {e}")
        return []

    jobs = []
    for item in data[:50]:
        try:
            title = item.get("position", "")
            if not any(kw in title.lower() for kw in kw_lower):
                tags = " ".join(item.get("tags", []))
                desc = item.get("description", "")
                if not any(kw in (tags + desc).lower() for kw in kw_lower):
                    continue

            job_url = item.get("url", "")
            if not job_url:
                continue

            jobs.append({
                "id": _job_id(job_url),
                "title": title,
                "company": item.get("company", ""),
                "location": "Remote",
                "url": job_url,
                "source": "remoteok",
                "description": item.get("description", "")[:4000],
                "match_score": 0,
                "keywords": item.get("tags", []),
            })
        except Exception:
            continue

    logger.info(f"RemoteOK: returning {len(jobs)} jobs")
    return jobs


# ── Dispatcher ────────────────────────────────────────────────────────────────

def scrape_all(config: dict) -> list[dict]:
    jobs = []
    jobs += scrape_remoteok(config)   # fastest, no login
    jobs += scrape_linkedin(config)
    jobs += scrape_indeed(config)
    # deduplicate by id
    seen = set()
    unique = []
    for j in jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            unique.append(j)
    logger.info(f"Total unique jobs scraped: {len(unique)}")
    return unique
