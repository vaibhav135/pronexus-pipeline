import asyncio
import json
import uuid as uuid_mod
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlmodel import select, desc

from app.api.schemas import (
    SearchRequest, SearchResponse, BusinessResponse,
    EnrichResponse,
    JobResponse, JobWithBusinessesResponse, BusinessWithEnrichment,
)
from app.database import get_session
from app.models.db import Business, Owner, Email, ScrapeJob, utcnow
from app.pipeline.discovery import fetch_google_maps_leads
from app.tasks.enrich import enrich_job

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_businesses(req: SearchRequest):
    """Search Google Maps for businesses, store results, and kick off enrichment."""
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

    # Fire enrichment in background via Celery
    enrich_job.delay(str(job.id))

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
    """Get a single job with its businesses and existing enrichment data."""
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

        enriched_businesses = []
        for b in businesses:
            owner_result = await session.execute(
                select(Owner).where(Owner.business_id == b.id)
            )
            owner = owner_result.scalars().first()

            email_result = await session.execute(
                select(Email).where(Email.business_id == b.id, Email.is_primary == True)
            )
            email = email_result.scalars().first()

            enriched_businesses.append(
                BusinessWithEnrichment(
                    business=BusinessResponse(
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
                    ),
                    owner_name=owner.name if owner else None,
                    owner_source=owner.source if owner else None,
                    email=email.email if email else None,
                    email_type=email.email_type if email else None,
                    email_source=email.source if email else None,
                    is_enriched=bool(owner),
                )
            )

    return JobWithBusinessesResponse(
        job=JobResponse(
            id=job.id,
            search_query=job.search_query,
            status=job.status,
            results_count=job.results_count,
            last_run_at=job.last_run_at,
            created_at=job.created_at,
        ),
        businesses=enriched_businesses,
    )


@router.get("/jobs/{job_id}/enrich-stream")
async def enrich_stream(job_id: uuid_mod.UUID):
    """
    SSE endpoint: streams enrichment progress by polling the DB.
    The actual enrichment runs in a Celery worker — this just reads results.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        async with get_session() as session:
            result = await session.execute(
                select(ScrapeJob).where(ScrapeJob.id == job_id)
            )
            job = result.scalars().first()
            if not job:
                yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                return

            biz_result = await session.execute(
                select(Business).where(Business.search_query == job.search_query)
            )
            businesses = biz_result.scalars().all()

        total = len(businesses)
        biz_ids = [b.id for b in businesses]
        biz_names = {b.id: b.name for b in businesses}
        sent: set[str] = set()

        while True:
            # Poll DB for newly enriched businesses
            async with get_session() as session:
                owner_result = await session.execute(
                    select(Owner).where(Owner.business_id.in_(biz_ids))
                )
                owners = {o.business_id: o for o in owner_result.scalars().all()}

                email_result = await session.execute(
                    select(Email).where(
                        Email.business_id.in_(biz_ids),
                        Email.is_primary == True,
                    )
                )
                emails = {e.business_id: e for e in email_result.scalars().all()}

            # Stream any new results
            for biz_id in biz_ids:
                str_id = str(biz_id)
                if str_id in sent:
                    continue

                owner = owners.get(biz_id)
                if not owner:
                    continue  # not enriched yet

                email = emails.get(biz_id)

                enriched = EnrichResponse(
                    business_id=biz_id,
                    business_name=biz_names[biz_id],
                    owner_name=owner.name,
                    owner_source=owner.source,
                    email=email.email if email else None,
                    email_type=email.email_type if email else None,
                    email_source=email.source if email else None,
                )
                yield f"event: result\ndata: {enriched.model_dump_json()}\n\n"
                sent.add(str_id)

            # Send progress
            progress = json.dumps({"completed": len(sent), "total": total})
            yield f"event: progress\ndata: {progress}\n\n"

            # All done?
            if len(sent) == total:
                yield f"event: done\ndata: {json.dumps({'message': 'All enrichments complete'})}\n\n"
                return

            # Poll interval
            await asyncio.sleep(3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
