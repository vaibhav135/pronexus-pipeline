"""
Website scraper — fetches homepage + internal pages, extracts text and emails.
One scrape, multiple extractions.
"""
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.config import settings

# Keywords to identify relevant internal pages
PAGE_KEYWORDS = re.compile(
    r"about|team|contact|staff|our-story|who-we-are|founder|owner|leadership|meet",
    re.IGNORECASE,
)

# Email regex — matches most standard email formats
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
)

# Emails to ignore
IGNORED_EMAIL_DOMAINS = {"example.com", "email.com", "yourdomain.com", "domain.com", "sentry.io", "wixpress.com"}
IGNORED_EMAIL_PREFIXES = {"noreply", "no-reply", "mailer-daemon", "postmaster", "webmaster"}


@dataclass
class ScrapedPage:
    url: str
    text: str
    emails: list[str] = field(default_factory=list)


@dataclass
class WebsiteData:
    pages: list[ScrapedPage]
    combined_text: str
    emails: list[str]  # deduplicated, filtered

    @property
    def has_content(self) -> bool:
        return len(self.combined_text) > 100


def _strip_html(html: str) -> str:
    """Strip HTML to clean text, removing boilerplate (nav, footer, ads, etc.)."""
    # Remove non-content elements
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<nav[^>]*>.*?</nav>", "", text, flags=re.DOTALL)
    text = re.sub(r"<footer[^>]*>.*?</footer>", "", text, flags=re.DOTALL)
    text = re.sub(r"<header[^>]*>.*?</header>", "", text, flags=re.DOTALL)
    text = re.sub(r"<aside[^>]*>.*?</aside>", "", text, flags=re.DOTALL)
    text = re.sub(r"<iframe[^>]*>.*?</iframe>", "", text, flags=re.DOTALL)
    text = re.sub(r"<svg[^>]*>.*?</svg>", "", text, flags=re.DOTALL)
    text = re.sub(r"<noscript[^>]*>.*?</noscript>", "", text, flags=re.DOTALL)
    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_emails(text: str) -> list[str]:
    """Extract valid email addresses from text."""
    raw_emails = EMAIL_PATTERN.findall(text)
    filtered = []
    seen = set()
    for email in raw_emails:
        email = email.lower().strip(".")
        domain = email.split("@")[1] if "@" in email else ""
        prefix = email.split("@")[0] if "@" in email else ""

        if email in seen:
            continue
        if domain in IGNORED_EMAIL_DOMAINS:
            continue
        if prefix in IGNORED_EMAIL_PREFIXES:
            continue
        # Skip image/file extensions mistakenly matched
        if domain.endswith((".png", ".jpg", ".gif", ".svg", ".css", ".js")):
            continue

        seen.add(email)
        filtered.append(email)

    return filtered


def _find_internal_page_urls(html: str, base_url: str) -> list[str]:
    """Find internal links that likely contain owner/contact info."""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)

    relevant = []
    seen = set()
    for href in all_hrefs:
        # Skip non-page links
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        # Only keep links matching keywords
        if not PAGE_KEYWORDS.search(href):
            continue

        # Make absolute
        if href.startswith("/"):
            url = f"{base}{href}"
        elif href.startswith("http"):
            # Only keep same-domain links
            if urlparse(href).netloc != parsed.netloc:
                continue
            url = href
        else:
            continue

        # Dedup
        url = url.rstrip("/")
        if url not in seen:
            seen.add(url)
            relevant.append(url)

    return relevant[:4]  # Max 4 subpages


async def _fetch_page(client: httpx.AsyncClient, url: str) -> ScrapedPage | None:
    """Fetch a single page, return stripped text and extracted emails."""
    try:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return None

        text = _strip_html(r.text)
        emails = _extract_emails(r.text)  # Extract from raw HTML (emails might be in href="mailto:")
        return ScrapedPage(url=url, text=text, emails=emails)
    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return None


async def _fetch_with_jina(url: str) -> ScrapedPage | None:
    """Fetch page via Jina Reader for JS-rendered content."""
    if not settings.jina_ai_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"https://r.jina.ai/{url}",
                headers={
                    "Authorization": f"Bearer {settings.jina_ai_api_key}",
                    "Accept": "text/plain",
                },
            )
            if r.status_code != 200:
                return None
            text = r.text
            emails = _extract_emails(text)
            return ScrapedPage(url=url, text=text, emails=emails)
    except Exception as e:
        logger.debug(f"Jina Reader failed for {url}: {e}")
        return None


async def scrape_website(website_url: str) -> WebsiteData:
    """
    Scrape a business website — homepage + relevant internal pages.
    Returns combined text and all extracted emails.
    """
    pages: list[ScrapedPage] = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        # 1. Fetch homepage
        homepage = await _fetch_page(client, website_url)
        if homepage:
            pages.append(homepage)

            # 2. Find and fetch internal pages
            try:
                r = await client.get(website_url, headers={"User-Agent": "Mozilla/5.0"})
                subpage_urls = _find_internal_page_urls(r.text, website_url)
            except Exception:
                subpage_urls = []

            for sub_url in subpage_urls:
                page = await _fetch_page(client, sub_url)
                if page:
                    pages.append(page)

    # 3. If httpx got thin content, try Jina on homepage
    combined_httpx = " ".join(p.text for p in pages)
    if len(combined_httpx) < 200:
        jina_page = await _fetch_with_jina(website_url)
        if jina_page:
            pages.append(jina_page)

    # 4. Combine results
    combined_text = "\n\n".join(f"--- {p.url} ---\n{p.text}" for p in pages)
    all_emails = []
    seen = set()
    for p in pages:
        for email in p.emails:
            if email not in seen:
                seen.add(email)
                all_emails.append(email)

    scraped = WebsiteData(
        pages=pages,
        combined_text=combined_text,
        emails=all_emails,
    )

    logger.info(
        f"Scraped {website_url}: {len(pages)} pages, "
        f"{len(combined_text)} chars, {len(all_emails)} emails"
    )
    return scraped
