import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    offset: int = 0
    country: str = "us"
    lang: str = "en"
    zoom: int = 12
    lat: str = ""
    lng: str = ""


class BusinessResponse(BaseModel):
    id: uuid.UUID
    place_id: str
    name: str
    types: list[str] | None = None
    full_address: str | None = None
    city: str | None = None
    state: str | None = None
    phone_number: str | None = None
    website: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rating: Decimal | None = None
    review_count: int | None = None
    verified: bool
    is_claimed: bool
    created_at: datetime


class SearchResponse(BaseModel):
    job_id: uuid.UUID
    query: str
    results_count: int
    businesses: list[BusinessResponse]


class EnrichResponse(BaseModel):
    business_id: uuid.UUID
    business_name: str
    owner_name: str | None = None
    owner_source: str | None = None
    email: str | None = None
    email_type: str | None = None
    email_source: str | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    search_query: str
    status: str
    results_count: int
    last_run_at: datetime | None = None
    created_at: datetime


class BusinessWithEnrichment(BaseModel):
    business: BusinessResponse
    owner_name: str | None = None
    owner_source: str | None = None
    email: str | None = None
    email_type: str | None = None
    email_source: str | None = None
    is_enriched: bool = False


class JobWithBusinessesResponse(BaseModel):
    job: JobResponse
    businesses: list[BusinessWithEnrichment]
