"""
Web scraper service.
Strategy:
  1. Try httpx (fast, no JS)
  2. Fallback to Playwright (handles JS-heavy pages like LinkedIn)
Returns cleaned plain text + original HTML.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger(__name__)

# Known JS-heavy domains that require Playwright
JS_HEAVY_DOMAINS = {
    "linkedin.com",
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "ashbyhq.com",
    "wellfound.com",
    "smartrecruiters.com",
    "icims.com",
    "taleo.net",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        parts = parsed.netloc.lower().split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return parsed.netloc.lower()
    except Exception:
        return ""


def _html_to_clean_text(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    soup = BeautifulSoup(html, "lxml")
    # Remove noise tags
    for tag in soup(["script", "style", "nav", "header", "footer", "iframe", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse blank lines
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", cleaned)


async def _fetch_with_httpx(url: str) -> tuple[str, str]:
    """Fetch page via simple HTTP GET. Returns (html, clean_text)."""
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        return html, _html_to_clean_text(html)


async def _fetch_with_playwright(url: str) -> tuple[str, str]:
    """Fetch JS-rendered page via headless Chromium. Returns (html, clean_text)."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="en-US",
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=45000)
            # Wait for job content to load
            await page.wait_for_timeout(2000)
            html = await page.content()
            await browser.close()
            return html, _html_to_clean_text(html)
    except Exception as e:
        logger.error("playwright_failed", url=url, error=str(e))
        raise


async def scrape_job_page(url: str) -> tuple[str, str]:
    """
    Scrape a job posting URL.
    Returns (original_html, clean_text).
    Raises httpx.HTTPError or RuntimeError on failure.
    """
    domain = _extract_domain(url)
    needs_js = any(js_domain in domain for js_domain in JS_HEAVY_DOMAINS)

    if needs_js:
        logger.info("scraping_with_playwright", url=url, domain=domain)
        try:
            return await _fetch_with_playwright(url)
        except Exception:
            logger.warning("playwright_failed_falling_back_to_httpx", url=url)
            return await _fetch_with_httpx(url)
    else:
        logger.info("scraping_with_httpx", url=url, domain=domain)
        try:
            return await _fetch_with_httpx(url)
        except Exception:
            logger.warning("httpx_failed_trying_playwright", url=url)
            return await _fetch_with_playwright(url)
