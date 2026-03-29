"""
Search fallback — Tavily → Exa waterfall.
Extracts both owner name and emails from search results.
"""
from dataclasses import dataclass, field

import httpx
from loguru import logger

from app.config import settings
from app.pipeline.owner_id import extract_owner_name
from app.pipeline.website_scraper import _extract_emails

SEARCH_QUERY_TEMPLATE = 'who is the owner of "{name}" {city} {state}'


@dataclass
class SearchResult:
    owner_name: str | None = None
    owner_source: str | None = None
    emails: list[str] = field(default_factory=list)
    email_source: str | None = None


async def _search_tavily(query: str) -> str | None:
    """Search using Tavily API. Returns combined result text or None."""
    if not settings.tavily_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": 5,
                    "include_answer": True,
                },
            )
            r.raise_for_status()
            data = r.json()

        parts = []
        if data.get("answer"):
            parts.append(data["answer"])
        for result in data.get("results", []):
            content = result.get("content", "")
            if content:
                parts.append(f"{result.get('title', '')}: {content}")

        return "\n".join(parts) if parts else None

    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return None


async def _search_exa(query: str) -> str | None:
    """Search using Exa API. Returns combined result text or None."""
    if not settings.exa_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": settings.exa_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "type": "auto",
                    "num_results": 5,
                    "contents": {
                        "highlights": {"max_characters": 4000},
                    },
                },
            )
            r.raise_for_status()
            data = r.json()

        parts = []
        for result in data.get("results", []):
            title = result.get("title", "")
            highlights = result.get("highlights", [])
            if highlights:
                parts.append(f"{title}: {' '.join(highlights)}")
            elif result.get("text"):
                parts.append(f"{title}: {result['text'][:500]}")

        return "\n".join(parts) if parts else None

    except Exception as e:
        logger.warning(f"Exa search failed: {e}")
        return None


def _extract_from_search_text(
    text: str,
    business_name: str,
    source_name: str,
) -> SearchResult:
    """Extract both owner name and emails from search result text."""
    result = SearchResult()

    owner = extract_owner_name(text, business_name)
    if owner:
        result.owner_name = owner
        result.owner_source = f"{source_name}_search"

    emails = _extract_emails(text)
    if emails:
        result.emails = emails
        result.email_source = f"{source_name}_search"

    return result


async def search_for_owner_and_email(
    business_name: str,
    city: str | None = None,
    state: str | None = None,
) -> SearchResult:
    """
    Search fallback waterfall: Tavily → Exa.
    Extracts both owner name and emails from results.
    """
    query = SEARCH_QUERY_TEMPLATE.format(
        name=business_name,
        city=city or "",
        state=state or "",
    ).strip()

    combined = SearchResult()

    # 1. Tavily
    tavily_text = await _search_tavily(query)
    if tavily_text:
        tavily_result = _extract_from_search_text(tavily_text, business_name, "tavily")
        if tavily_result.owner_name:
            combined.owner_name = tavily_result.owner_name
            combined.owner_source = tavily_result.owner_source
            logger.info(f"Owner found via Tavily: {combined.owner_name}")
        if tavily_result.emails:
            combined.emails = tavily_result.emails
            combined.email_source = tavily_result.email_source

    # If we have both, we're done
    if combined.owner_name and combined.emails:
        return combined

    # 2. Exa — only search if still missing something
    exa_text = await _search_exa(query)
    if exa_text:
        exa_result = _extract_from_search_text(exa_text, business_name, "exa")
        if not combined.owner_name and exa_result.owner_name:
            combined.owner_name = exa_result.owner_name
            combined.owner_source = exa_result.owner_source
            logger.info(f"Owner found via Exa: {combined.owner_name}")
        if not combined.emails and exa_result.emails:
            combined.emails = exa_result.emails
            combined.email_source = exa_result.email_source

    return combined
