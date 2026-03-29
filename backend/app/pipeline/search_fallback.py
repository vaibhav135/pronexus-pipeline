import httpx
from loguru import logger

from app.config import settings
from app.pipeline.owner_id import _extract_name_with_groq

SEARCH_QUERY_TEMPLATE = 'who is the owner of "{name}" {city} {state}'


async def _search_tavily(query: str) -> str | None:
    """Search using Tavily API. Returns search result text or None."""
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

        # Collect answer + result snippets
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
    """Search using Exa API. Returns search result text or None."""
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


async def search_for_owner(
    business_name: str,
    city: str | None = None,
    state: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Search fallback waterfall: Tavily → Exa.
    Returns (owner_name, source) or (None, None).
    """
    query = SEARCH_QUERY_TEMPLATE.format(
        name=business_name,
        city=city or "",
        state=state or "",
    ).strip()

    # 1. Tavily
    tavily_text = await _search_tavily(query)
    if tavily_text:
        name = _extract_name_with_groq(tavily_text, business_name)
        if name:
            logger.info(f"Owner found via Tavily: {name}")
            return name, "tavily_search"

    # 2. Exa
    exa_text = await _search_exa(query)
    if exa_text:
        name = _extract_name_with_groq(exa_text, business_name)
        if name:
            logger.info(f"Owner found via Exa: {name}")
            return name, "exa_search"

    return None, None
