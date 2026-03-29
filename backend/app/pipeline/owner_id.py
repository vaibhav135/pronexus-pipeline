import re

import httpx
from groq import Groq
from loguru import logger

from app.config import settings

EXTRACTION_PROMPT = (
    "Extract the business owner or founder's full name from this text. "
    "Return ONLY the full name as a plain string, or \"not found\" if not mentioned. "
    "Rules: "
    "- The name MUST appear explicitly in the text. Do NOT invent or guess names. "
    "- Do NOT return placeholder names like John Doe, Jane Doe, John Smith. "
    "- Do NOT extract customer names from testimonials or reviews. "
    "- Do NOT include titles like Mr., Dr., Owner:, CEO:. "
    "- If you are not confident the person is the owner/founder, return \"not found\"."
)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_name_with_groq(text: str, business_name: str) -> str | None:
    """Send text to Groq and extract owner name."""
    client = Groq(api_key=settings.groq_api_key)
    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"Business: {business_name}\n\nText:\n{text[:3000]}"},
        ],
        temperature=0,
        max_completion_tokens=50,
    )
    answer = completion.choices[0].message.content.strip()

    if answer.lower() in ("not found", "none", "n/a", "null", ""):
        return None

    # Basic cleanup — remove quotes, periods
    answer = answer.strip("\"'.")
    if len(answer) < 3 or len(answer) > 100:
        return None

    return answer


async def _scrape_with_httpx(url: str) -> str | None:
    """Fetch website with plain httpx, strip HTML."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return None
            return _strip_html(r.text)
    except Exception as e:
        logger.debug(f"httpx scrape failed for {url}: {e}")
        return None


async def _scrape_with_jina(url: str) -> str | None:
    """Fetch website via Jina Reader API — renders JS, returns markdown."""
    if not settings.jina_ai_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(
                f"https://r.jina.ai/{url}",
                headers={
                    "Authorization": f"Bearer {settings.jina_ai_api_key}",
                    "Accept": "text/plain",
                },
            )
            if r.status_code != 200:
                return None
            return r.text
    except Exception as e:
        logger.debug(f"Jina Reader failed for {url}: {e}")
        return None


async def _find_about_pages(base_url: str, html: str) -> list[str]:
    """Find about/team/contact page URLs from the homepage HTML."""
    pattern = r'href=["\']([^"\']*(?:about|team|our-story|contact|who-we-are)[^"\']*)["\']'
    links = re.findall(pattern, html, re.IGNORECASE)

    about_urls = []
    for link in links:
        if link.startswith("http"):
            about_urls.append(link)
        elif link.startswith("/"):
            # Make absolute URL
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            about_urls.append(f"{parsed.scheme}://{parsed.netloc}{link}")

    # Deduplicate
    return list(dict.fromkeys(about_urls))[:3]


async def extract_from_website(website_url: str, business_name: str) -> tuple[str | None, str | None]:
    """
    Try to extract owner name from business website.
    Returns (owner_name, source) or (None, None).
    """
    # 1. Try httpx on homepage
    homepage_html = await _scrape_with_httpx(website_url)
    if homepage_html:
        name = _extract_name_with_groq(homepage_html, business_name)
        if name:
            logger.info(f"Owner found via httpx homepage: {name}")
            return name, "website_httpx"

        # 2. Try about/team/contact pages
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            try:
                r = await client.get(website_url, headers={"User-Agent": "Mozilla/5.0"})
                about_urls = await _find_about_pages(website_url, r.text)
            except Exception:
                about_urls = []

        for about_url in about_urls:
            about_text = await _scrape_with_httpx(about_url)
            if about_text:
                name = _extract_name_with_groq(about_text, business_name)
                if name:
                    logger.info(f"Owner found via httpx about page: {name}")
                    return name, "website_httpx"

    # 3. Try Jina Reader (JS rendering)
    jina_text = await _scrape_with_jina(website_url)
    if jina_text:
        name = _extract_name_with_groq(jina_text, business_name)
        if name:
            logger.info(f"Owner found via Jina Reader: {name}")
            return name, "website_jina"

    return None, None


async def identify_owner(
    website_url: str | None,
    business_name: str,
    city: str | None = None,
    state: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Full owner identification waterfall.
    Returns (owner_name, source) or (None, None).

    Waterfall:
    1. Scrape website (httpx → about pages → Jina Reader)
    2. Tavily search
    3. Exa search
    """
    # Step 1: Website scraping
    if website_url:
        name, source = await extract_from_website(website_url, business_name)
        if name:
            return name, source

    # Step 2: Search fallback
    from app.pipeline.search_fallback import search_for_owner
    name, source = await search_for_owner(business_name, city, state)
    if name:
        return name, source

    logger.info(f"Owner not found for {business_name}")
    return None, None
