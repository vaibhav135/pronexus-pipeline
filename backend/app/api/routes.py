import json
import uuid as uuid_mod
from datetime import datetime, timezone
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlmodel import select, desc

from app.api.schemas import (
    SearchRequest, SearchResponse, BusinessResponse,
    EnrichRequest, EnrichResponse,
    JobResponse, JobWithBusinessesResponse,
)
from app.database import get_session
from app.models.db import Business, Owner, Email, ScrapeJob, utcnow
from app.pipeline.discovery import fetch_google_maps_leads
from app.pipeline.owner_id import identify_owner
from app.pipeline.search_fallback import search_for_owner_and_email
from app.pipeline.email_finder import find_email

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


@router.post("/enrich", response_model=EnrichResponse)
async def enrich_business(req: EnrichRequest):
    """
    Enrich a business with owner name and email.

    Pipeline:
    1. Scrape website → extract owner name + emails
    2. If missing → search fallback (Tavily → Exa) → extract both
    3. If still missing email → Prospeo → Hunter
    """
    async with get_session() as session:
        # Get business
        result = await session.execute(
            select(Business).where(Business.id == req.business_id)
        )
        biz = result.scalars().first()
        if not biz:
            raise HTTPException(status_code=404, detail="Business not found")

        # Check if already enriched
        owner_result = await session.execute(
            select(Owner).where(Owner.business_id == biz.id)
        )
        existing_owner = owner_result.scalars().first()

        email_result = await session.execute(
            select(Email).where(Email.business_id == biz.id, Email.is_primary == True)
        )
        existing_email = email_result.scalars().first()

        if existing_owner and existing_owner.name and existing_email:
            return EnrichResponse(
                business_id=biz.id,
                business_name=biz.name,
                owner_name=existing_owner.name,
                owner_source=existing_owner.source,
                email=existing_email.email,
                email_type=existing_email.email_type,
                email_source=existing_email.source,
            )

        # Step 1: Owner ID (scrapes website internally, returns website_data)
        owner_name, owner_source, website_data = await identify_owner(
            website_url=biz.website,
            business_name=biz.name,
            city=biz.city,
            state=biz.state,
        )

        # Emails from website scrape
        website_emails = website_data.emails if website_data else []

        # Step 2: If missing owner or email, search fallback already ran in identify_owner
        # But we need emails from search too
        email_from_search = None
        email_search_source = None
        if not website_emails:
            search_result = await search_for_owner_and_email(biz.name, biz.city, biz.state)
            if not owner_name and search_result.owner_name:
                owner_name = search_result.owner_name
                owner_source = search_result.owner_source
            if search_result.emails:
                website_emails = search_result.emails
                email_search_source = search_result.email_source

        # Step 3: Email fallback (Prospeo → Hunter)
        best_email, email_type, email_source = await find_email(
            website_url=biz.website,
            owner_name=owner_name,
            existing_emails=website_emails,
        )

        # Use search source if email came from there
        if email_source == "website" and email_search_source:
            email_source = email_search_source

        # Store owner
        if owner_name and not existing_owner:
            owner = Owner(
                business_id=biz.id,
                name=owner_name,
                source=owner_source,
                confidence="high" if owner_source and "website" in owner_source else "medium",
            )
            session.add(owner)

        # Store email
        if best_email and not existing_email:
            email_record = Email(
                business_id=biz.id,
                email=best_email,
                email_type=email_type,
                source=email_source,
                verification_status="unverified",
                is_primary=True,
            )
            session.add(email_record)

    return EnrichResponse(
        business_id=biz.id,
        business_name=biz.name,
        owner_name=owner_name,
        owner_source=owner_source,
        email=best_email,
        email_type=email_type,
        email_source=email_source,
    )


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs():
    """List all search jobs, most recent first."""
    async with get_session() as session:
        result = await session.execute(
            select(ScrapeJob).order_by(desc(ScrapeJob.created_at)).limit(50)
        )
        jobs = result.scalars().all()

    return [
        JobResponse(
            id=j.id,
            search_query=j.search_query,
            status=j.status,
            results_count=j.results_count,
            last_run_at=j.last_run_at,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobWithBusinessesResponse)
async def get_job(job_id: uuid_mod.UUID):
    """Get a single job with its businesses."""
    async with get_session() as session:
        result = await session.execute(
            select(ScrapeJob).where(ScrapeJob.id == job_id)
        )
        job = result.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        biz_result = await session.execute(
            select(Business).where(Business.search_query == job.search_query)
        )
        businesses = biz_result.scalars().all()

    return JobWithBusinessesResponse(
        job=JobResponse(
            id=job.id,
            search_query=job.search_query,
            status=job.status,
            results_count=job.results_count,
            last_run_at=job.last_run_at,
            created_at=job.created_at,
        ),
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
            for b in businesses
        ],
    )


@router.get("/jobs/{job_id}/enrich-stream")
async def enrich_stream(job_id: uuid_mod.UUID):
    """SSE endpoint: enriches all businesses for a job, streaming results."""

    async def event_generator() -> AsyncGenerator[str, None]:
        async with get_session() as session:
            # Get job
            result = await session.execute(
                select(ScrapeJob).where(ScrapeJob.id == job_id)
            )
            job = result.scalars().first()
            if not job:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                return

            # Get businesses for this job
            biz_result = await session.execute(
                select(Business).where(Business.search_query == job.search_query)
            )
            businesses = biz_result.scalars().all()

        total = len(businesses)
        completed = 0

        for biz in businesses:
            try:
                # Check if already enriched
                async with get_session() as session:
                    owner_result = await session.execute(
                        select(Owner).where(Owner.business_id == biz.id)
                    )
                    existing_owner = owner_result.scalars().first()

                    email_result = await session.execute(
                        select(Email).where(Email.business_id == biz.id, Email.is_primary == True)
                    )
                    existing_email = email_result.scalars().first()

                if existing_owner and existing_owner.name and existing_email:
                    # Already enriched — send cached result
                    enriched = EnrichResponse(
                        business_id=biz.id,
                        business_name=biz.name,
                        owner_name=existing_owner.name,
                        owner_source=existing_owner.source,
                        email=existing_email.email,
                        email_type=existing_email.email_type,
                        email_source=existing_email.source,
                    )
                else:
                    # Run enrichment pipeline
                    owner_name, owner_source, website_data = await identify_owner(
                        website_url=biz.website,
                        business_name=biz.name,
                        city=biz.city,
                        state=biz.state,
                    )

                    website_emails = website_data.emails if website_data else []

                    email_from_search = None
                    email_search_source = None
                    if not website_emails:
                        search_result = await search_for_owner_and_email(biz.name, biz.city, biz.state)
                        if not owner_name and search_result.owner_name:
                            owner_name = search_result.owner_name
                            owner_source = search_result.owner_source
                        if search_result.emails:
                            website_emails = search_result.emails
                            email_search_source = search_result.email_source

                    best_email, email_type, email_source = await find_email(
                        website_url=biz.website,
                        owner_name=owner_name,
                        existing_emails=website_emails,
                    )

                    if email_source == "website" and email_search_source:
                        email_source = email_search_source

                    # Store results
                    async with get_session() as session:
                        if owner_name and not existing_owner:
                            owner = Owner(
                                business_id=biz.id,
                                name=owner_name,
                                source=owner_source,
                                confidence="high" if owner_source and "website" in owner_source else "medium",
                            )
                            session.add(owner)

                        if best_email and not (existing_email):
                            email_record = Email(
                                business_id=biz.id,
                                email=best_email,
                                email_type=email_type,
                                source=email_source,
                                verification_status="unverified",
                                is_primary=True,
                            )
                            session.add(email_record)

                    enriched = EnrichResponse(
                        business_id=biz.id,
                        business_name=biz.name,
                        owner_name=owner_name,
                        owner_source=owner_source,
                        email=best_email,
                        email_type=email_type,
                        email_source=email_source,
                    )

                completed += 1
                yield f"event: result\ndata: {enriched.model_dump_json()}\n\n"

            except Exception as e:
                completed += 1
                logger.error(f"Enrichment failed for {biz.name}: {e}")
                error_data = json.dumps({
                    "business_id": str(biz.id),
                    "business_name": biz.name,
                    "error": str(e),
                })
                yield f"event: error\ndata: {error_data}\n\n"

            # Send progress
            progress = json.dumps({"completed": completed, "total": total})
            yield f"event: progress\ndata: {progress}\n\n"

        yield f"event: done\ndata: {json.dumps({'message': 'All enrichments complete'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
