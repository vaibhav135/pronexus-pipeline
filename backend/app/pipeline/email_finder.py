"""
Email finding fallback — Prospeo.
Only called when website scraping and search didn't find an email.
"""
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.config import settings


def extract_domain(url: str) -> str | None:
    """Extract domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


def _is_generic_email(email: str) -> bool:
    """Check if an email is a generic address (info@, contact@, etc.)."""
    generic_prefixes = {
        "info", "contact", "hello", "admin", "support",
        "sales", "office", "team", "mail", "noreply", "no-reply",
    }
    prefix = email.split("@")[0].lower()
    return prefix in generic_prefixes


async def find_email_prospeo(owner_name: str, domain: str) -> str | None:
    """
    Find personal email via Prospeo.
    Only call when owner name is known AND no personal email found.
    """
    if not settings.prospeo_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.prospeo.io/email-finder",
                headers={
                    "X-KEY": settings.prospeo_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "full_name": owner_name,
                    "domain": domain,
                },
            )
            data = r.json()

            email = data.get("response", {}).get("email")
            if email:
                logger.info(f"Prospeo found email: {email}")
                return email

    except Exception as e:
        logger.warning(f"Prospeo failed for {owner_name}@{domain}: {e}")

    return None


async def find_email(
    website_url: str | None,
    owner_name: str | None,
    existing_emails: list[str] | None = None,
) -> tuple[str | None, str | None, str | None]:
    """
    Email finding waterfall.
    Returns (email, email_type, source) or (None, None, None).

    1. Check existing emails from website/search scrape
    2. Prospeo (owner name + domain → personal email)
    """
    # Check if we already have a good email
    if existing_emails:
        personal = [e for e in existing_emails if not _is_generic_email(e)]
        if personal:
            return personal[0], "personal", "website"
        return existing_emails[0], "generic", "website"

    domain = extract_domain(website_url) if website_url else None
    if not domain:
        return None, None, None

    # Prospeo — only if we have owner name
    if owner_name:
        email = await find_email_prospeo(owner_name, domain)
        if email:
            return email, "personal", "prospeo"

    return None, None, None
