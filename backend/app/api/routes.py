from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from loguru import logger
from sqlmodel import select

from app.api.schemas import SearchRequest, SearchResponse, BusinessResponse
from app.database import get_session
from app.models.db import Business, ScrapeJob, utcnow
from app.pipeline.discovery import fetch_google_maps_leads

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_businesses(req: SearchRequest):
    """Search Google Maps for businesses and store results."""
    async with get_session() as session:
        # Create or get existing ScrapeJob
        result = await session.execute(
            select(ScrapeJob).where(ScrapeJob.search_query == req.query)
        )
        job = result.scalars().first()

        if job:
            job.status = "running"
            job.last_run_at = utcnow()
        else:
            job = ScrapeJob(search_query=req.query, status="running", last_run_at=utcnow())
            session.add(job)
        await session.flush()

        # Fetch from Scraper Tech
        try:
            leads = await fetch_google_maps_leads(
                query=req.query,
                limit=req.limit,
                offset=req.offset,
                country=req.country,
                lang=req.lang,
                zoom=req.zoom,
                lat=req.lat,
                lng=req.lng,
            )
        except Exception as e:
            job.status = "failed"
            logger.error(f"Discovery failed for '{req.query}': {e}")
            raise HTTPException(status_code=502, detail=f"Scraper Tech API error: {str(e)}")

        # Upsert businesses by place_id
        stored = []
        for lead in leads:
            result = await session.execute(
                select(Business).where(Business.place_id == lead["place_id"])
            )
            biz = result.scalars().first()

            if biz:
                # Update existing record
                for key, value in lead.items():
                    if value is not None:
                        setattr(biz, key, value)
                biz.updated_at = utcnow()
            else:
                biz = Business(**lead)
                session.add(biz)

            await session.flush()
            stored.append(biz)

        # Update job status
        job.status = "completed"
        job.results_count = len(stored)

    return SearchResponse(
        job_id=job.id,
        query=req.query,
        results_count=len(stored),
        businesses=[
            BusinessResponse(
                id=b.id,
                place_id=b.place_id,
                name=b.name,
                types=b.types,
                full_address=b.full_address,
                city=b.city,
                state=b.state,
                phone_number=b.phone_number,
                website=b.website,
                latitude=b.latitude,
                longitude=b.longitude,
                rating=b.rating,
                review_count=b.review_count,
                verified=b.verified,
                is_claimed=b.is_claimed,
                created_at=b.created_at,
            )
            for b in stored
        ],
    )
