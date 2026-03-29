"""
Owner identification — extracts owner name from scraped website data or search results.
"""
from groq import Groq
from loguru import logger

from app.config import settings
from app.pipeline.website_scraper import WebsiteData, scrape_website

EXTRACTION_PROMPT = (
    "Extract the business owner or founder's full name from this text. "
    "Return ONLY the full name as a plain string, or \"not found\" if not mentioned. "
    "Rules: "
    "- The name MUST appear explicitly in the text. Do NOT invent or guess names. "
    "- Do NOT return placeholder names like John Doe, Jane Doe. "
    "- Do NOT extract customer names from testimonials or reviews. "
    "- Do NOT include titles like Mr., Dr., Owner:, CEO:. "
    "- If you are not confident the person is the owner/founder, return \"not found\"."
)


def extract_owner_name(text: str, business_name: str) -> str | None:
    """Extract owner name from text using Groq LLM."""
    if not text or len(text) < 50:
        return None

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
    answer = answer.strip("\"'.")

    if answer.lower() in ("not found", "none", "n/a", "null", "not mentioned", ""):
        return None
    if len(answer) < 3 or len(answer) > 100:
        return None

    return answer


async def identify_owner(
    website_url: str | None,
    business_name: str,
    city: str | None = None,
    state: str | None = None,
    website_data: WebsiteData | None = None,
) -> tuple[str | None, str | None, WebsiteData | None]:
    """
    Full owner identification waterfall.
    Returns (owner_name, source, website_data).

    Waterfall:
    1. Extract from website data (reuse if already scraped)
    2. Tavily search
    3. Exa search
    """
    # Step 1: Website scraping
    if website_url and not website_data:
        website_data = await scrape_website(website_url)

    if website_data and website_data.has_content:
        name = extract_owner_name(website_data.combined_text, business_name)
        if name:
            source = "website_jina" if any("r.jina.ai" in p.url for p in website_data.pages) else "website_httpx"
            logger.info(f"Owner found via {source}: {name}")
            return name, source, website_data

    # Step 2: Search fallback — returns both owner and emails from search
    from app.pipeline.search_fallback import search_for_owner_and_email
    search_result = await search_for_owner_and_email(business_name, city, state)

    # Attach search emails to website_data so they're not lost
    if search_result.emails and website_data:
        website_data.emails = search_result.emails
    elif search_result.emails and not website_data:
        website_data = WebsiteData(pages=[], combined_text="", emails=search_result.emails)

    if search_result.owner_name:
        return search_result.owner_name, search_result.owner_source, website_data

    logger.info(f"Owner not found for {business_name}")
    return None, None, website_data
