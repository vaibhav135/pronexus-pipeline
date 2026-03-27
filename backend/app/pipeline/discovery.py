import httpx
from loguru import logger

from app.config import settings

SCRAPER_TECH_URL = "https://api.scraper.tech/searchmaps.php"


def parse_city_state(raw_city: str | None) -> tuple[str | None, str | None]:
    """Parse 'Pipe Creek, TX' into ('Pipe Creek', 'TX')."""
    if not raw_city:
        return None, None
    parts = [p.strip() for p in raw_city.split(",")]
    if len(parts) == 2:
        return parts[0], parts[1]
    return raw_city, None


def parse_business(raw: dict, search_query: str) -> dict:
    """Transform raw API response into our Business fields."""
    city, state = parse_city_state(raw.get("city"))
    return {
        "place_id": raw["place_id"],
        "business_id": raw.get("business_id"),
        "name": raw["name"],
        "types": raw.get("types"),
        "full_address": raw.get("full_address"),
        "city": city,
        "state": state,
        "phone_number": raw.get("phone_number"),
        "website": raw.get("website"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "rating": raw.get("rating"),
        "review_count": raw.get("review_count"),
        "verified": raw.get("verified", False),
        "is_claimed": raw.get("is_claimed", False),
        "is_permanently_closed": raw.get("is_permanently_closed", False),
        "working_hours": raw.get("working_hours"),
        "place_link": raw.get("place_link"),
        "source": "google_maps",
        "search_query": search_query,
    }


async def fetch_google_maps_leads(
    query: str,
    limit: int = 20,
    country: str = "us",
    lang: str = "en",
    offset: int = 0,
    zoom: int = 12,
    lat: str = "",
    lng: str = "",
) -> list[dict]:
    """Fetch businesses from Scraper Tech Google Maps API."""
    headers = {"scraper-key": settings.map_scraper}
    params = {
        "query": query,
        "limit": limit,
        "country": country,
        "lang": lang,
        "lat": lat,
        "lng": lng,
        "offset": offset,
        "zoom": zoom,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(SCRAPER_TECH_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "ok":
        logger.error(f"Scraper Tech returned status: {data.get('status')}")
        return []

    raw_businesses = data.get("data", [])
    results = []
    for raw in raw_businesses:
        # Skip closed businesses
        if raw.get("is_permanently_closed"):
            continue
        results.append(parse_business(raw, query))

    logger.info(f"Fetched {len(results)} businesses for query: {query}")
    return results
