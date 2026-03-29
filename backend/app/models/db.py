import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text, Index, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
import sqlalchemy as sa


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Business(SQLModel, table=True):
    __tablename__ = "businesses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    place_id: str = Field(max_length=255, unique=True, index=True)
    business_id: str | None = Field(default=None, max_length=255)
    name: str = Field(max_length=500)
    types: list[str] | None = Field(default=None, sa_column=Column(ARRAY(sa.String)))
    full_address: str | None = Field(default=None, sa_column=Column(Text))
    city: str | None = Field(default=None, max_length=255)
    state: str | None = Field(default=None, max_length=10)
    phone_number: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, sa_column=Column(Text))
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    rating: Decimal | None = Field(default=None, max_digits=2, decimal_places=1)
    review_count: int | None = Field(default=None)
    verified: bool = Field(default=False)
    is_claimed: bool = Field(default=False)
    is_permanently_closed: bool = Field(default=False)
    working_hours: dict | None = Field(default=None, sa_column=Column(JSONB))
    place_link: str | None = Field(default=None, sa_column=Column(Text))
    source: str = Field(default="google_maps", max_length=50)
    search_query: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), default=utcnow))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), default=utcnow))

    __table_args__ = (
        Index("idx_businesses_city_state", "city", "state"),
    )


class Owner(SQLModel, table=True):
    __tablename__ = "owners"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    business_id: uuid.UUID = Field(foreign_key="businesses.id", index=True)
    name: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=50)  # "website_httpx" | "website_jina" | "tavily_search" | "exa_search"
    confidence: str | None = Field(default=None, max_length=20)  # "high" | "medium" | "low"
    raw_response: dict | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), default=utcnow))


class ScrapeJob(SQLModel, table=True):
    __tablename__ = "scrape_jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    search_query: str = Field(max_length=500, unique=True)
    status: str = Field(default="pending", max_length=50)  # "pending" | "running" | "completed" | "failed"
    results_count: int = Field(default=0)
    last_run_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), default=utcnow))
