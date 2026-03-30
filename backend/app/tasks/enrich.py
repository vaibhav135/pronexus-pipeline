"""
Celery task for enriching all businesses in a job.
Resumable — skips businesses that already have an Owner row.
"""
import asyncio

from loguru import logger
from sqlmodel import select

from app.worker import celery_app
from app.database import get_session
from app.models.db import Business, Owner, Email, ScrapeJob
from app.pipeline.owner_id import identify_owner
from app.pipeline.email_finder import find_email


async def _enrich_single_business(biz: Business) -> None:
    """Run the full enrichment pipeline for one business and save results."""
    # Check if already enriched (Owner row exists = already attempted)
    async with get_session() as session:
        owner_result = await session.execute(
            select(Owner).where(Owner.business_id == biz.id)
        )
        existing_owner = owner_result.scalars().first()

    if existing_owner:
        logger.debug(f"Skipping {biz.name} — already enriched")
        return

    logger.info(f"Enriching: {biz.name}")

    # Step 1: Identify owner (also scrapes website + search fallback)
    owner_name, owner_source, website_data = await identify_owner(
        website_url=biz.website,
        business_name=biz.name,
        city=biz.city,
        state=biz.state,
    )

    # Step 2: Find email (website/search emails already in website_data)
    website_emails = website_data.emails if website_data else []

    best_email, email_type, email_source = await find_email(
        website_url=biz.website,
        owner_name=owner_name,
        existing_emails=website_emails,
    )

    # Step 3: Save results — always create Owner row to mark enrichment attempted
    async with get_session() as session:
        owner = Owner(
            business_id=biz.id,
            name=owner_name,
            source=owner_source if owner_name else "not_found",
            confidence="high" if owner_source and "website" in owner_source else "medium" if owner_name else "none",
        )
        session.add(owner)

        if best_email:
            email_record = Email(
                business_id=biz.id,
                email=best_email,
                email_type=email_type,
                source=email_source,
                verification_status="unverified",
                is_primary=True,
            )
            session.add(email_record)

    logger.info(
        f"Enriched {biz.name}: owner={owner_name or 'not found'}, email={best_email or 'not found'}"
    )


async def _enrich_job_async(job_id: str) -> None:
    """Enrich all businesses for a job. Skips already-enriched ones."""
    async with get_session() as session:
        result = await session.execute(
            select(ScrapeJob).where(ScrapeJob.id == job_id)
        )
        job = result.scalars().first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        biz_result = await session.execute(
            select(Business).where(Business.search_query == job.search_query)
        )
        businesses = biz_result.scalars().all()

    total = len(businesses)
    logger.info(f"Starting enrichment for job {job_id}: {total} businesses")

    for i, biz in enumerate(businesses, 1):
        try:
            await _enrich_single_business(biz)
        except Exception as e:
            logger.error(f"Failed to enrich {biz.name} ({i}/{total}): {e}")
            continue

    logger.info(f"Enrichment complete for job {job_id}")


@celery_app.task(bind=True, max_retries=2)
def enrich_job(self, job_id: str) -> None:
    """Celery task: enrich all businesses for a job."""
    try:
        asyncio.run(_enrich_job_async(job_id))
    except Exception as e:
        logger.error(f"enrich_job failed for {job_id}: {e}")
        raise self.retry(exc=e, countdown=30)
