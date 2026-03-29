from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from loguru import logger
from sqlmodel import select

from app.api.schemas import SearchRequest, SearchResponse, BusinessResponse, OwnerIdentifyRequest, OwnerResponse
from app.database import get_session
from app.models.db import Business, Owner, ScrapeJob, utcnow
from app.pipeline.discovery import fetch_google_maps_leads
from app.pipeline.owner_id import identify_owner

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


@router.post("/owner-id", response_model=OwnerResponse)
async def identify_business_owner(req: OwnerIdentifyRequest):
    """Identify the owner of a business using the waterfall pipeline."""
    async with get_session() as session:
        # Get business
        result = await session.execute(
            select(Business).where(Business.id == req.business_id)
        )
        biz = result.scalars().first()
        if not biz:
            raise HTTPException(status_code=404, detail="Business not found")

        # Check if owner already identified
        result = await session.execute(
            select(Owner).where(Owner.business_id == biz.id)
        )
        existing_owner = result.scalars().first()
        if existing_owner and existing_owner.name:
            return OwnerResponse(
                business_id=biz.id,
                business_name=biz.name,
                owner_name=existing_owner.name,
                source=existing_owner.source,
                confidence=existing_owner.confidence,
            )

        # Run waterfall
        owner_name, source = await identify_owner(
            website_url=biz.website,
            business_name=biz.name,
            city=biz.city,
            state=biz.state,
        )

        # Store result
        owner = Owner(
            business_id=biz.id,
            name=owner_name,
            source=source,
            confidence="high" if source and "website" in source else "medium" if source else None,
        )
        session.add(owner)

    return OwnerResponse(
        business_id=biz.id,
        business_name=biz.name,
        owner_name=owner_name,
        source=source,
        confidence=owner.confidence,
    )
