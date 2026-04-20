"""SQLModel table models and Pydantic response models.

Request body validation is handled manually in each router — there are no
Pydantic BaseModel subclasses used as FastAPI request body parameters here.
Response models (output serialization) still use Pydantic BaseModel.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Enum as SAEnum, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class PaperStatus(str, Enum):
    to_read = "to_read"
    reading = "reading"
    completed = "completed"


# --- Database tables (SQLModel) ---


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperKeyword(SQLModel, table=True):
    paper_id: int = Field(foreign_key="paper.id", primary_key=True)
    keyword_id: int = Field(foreign_key="keyword.id", primary_key=True)


# ARCHITECTURE NOTE — Domain + Infrastructure blending
# In an ideal separation, `Paper` would be a plain Python class (domain layer)
# with no database knowledge: just fields, business rules, and state transitions.
# A separate ORM class (infrastructure layer) would handle the SQLAlchemy mapping.
#
# SQLModel collapses both into one class as a deliberate convenience trade-off.
# The blending is visible in three places:
#   1. `table=True`          — turns this domain concept into a DB table definition
#   2. `sa_column=Column(…)` — SQLAlchemy column types leaking into field declarations
#   3. `Relationship(…)`     — ORM relationship machinery instead of plain Python references
#
# This is acceptable for a project of this size, but means:
#   - You need a DB session to instantiate Paper in tests
#   - Swapping the ORM would require touching business model code
#   - DB schema concerns (column types, indexes) live next to business concerns (status, keywords)
class Paper(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    authors: str = Field(default="")
    doi: Optional[str] = Field(default=None, index=True)
    arxiv_id: Optional[str] = Field(default=None, index=True)
    status: PaperStatus = Field(
        default=PaperStatus.to_read,
        sa_column=Column(SAEnum(PaperStatus, native_enum=False, length=32)),
    )
    file_path: Optional[str] = None
    search_document: str = Field(default="", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    last_opened_at: Optional[datetime] = None
    user_id: int = Field(foreign_key="users.id")

    keywords: list["Keyword"] = Relationship(
        back_populates="papers",
        link_model=PaperKeyword,
    )
    daily_logs: list["DailyLog"] = Relationship(back_populates="paper")


class Keyword(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", name="uq_keyword_name"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)

    papers: list["Paper"] = Relationship(
        back_populates="keywords",
        link_model=PaperKeyword,
    )


class DailyLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    paper_id: int = Field(foreign_key="paper.id")
    user_id: int = Field(foreign_key="users.id", index=True)
    activity_date: date = Field(index=True)

    paper: Optional[Paper] = Relationship(back_populates="daily_logs")


# --- API-only Pydantic models (no table=True) ---


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PaperKeywordOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class PaperOut(BaseModel):
    id: int
    title: str
    authors: str
    doi: Optional[str]
    arxiv_id: Optional[str]
    status: PaperStatus
    file_path: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    last_opened_at: Optional[datetime]
    user_id: int
    keywords: list[PaperKeywordOut] = []

    model_config = {"from_attributes": True}


class HeatmapDay(BaseModel):
    date: date
    count: int


class HeatmapResponse(BaseModel):
    days: list[HeatmapDay]


class MeStatsResponse(BaseModel):
    total_read: int
    active_keyword_count: int
    top_keywords: list[dict]
    recently_read: list[PaperOut]
    recently_opened: list[PaperOut]


# --- PubMed discovery models (no table=True — never persisted directly) ---


class PaperDiscoverResult(BaseModel):
    """A single paper returned from an external discovery source (e.g. PubMed).

    This is never written to the database by the search endpoint.
    The import endpoint turns one of these into a Paper row.
    """

    source: str = "pubmed"
    external_id: str                  # PMID for PubMed
    title: str
    authors: list[str]
    abstract: Optional[str] = None
    journal: Optional[str] = None
    published_date: Optional[str] = None   # "YYYY" or "YYYY-MM"
    doi: Optional[str] = None
    doi_url: Optional[str] = None     # https://doi.org/{doi} — publisher landing page
    pmc_url: Optional[str] = None     # PMC full-text URL if open-access copy exists
    pubmed_url: Optional[str] = None  # PubMed abstract page
    in_library: bool = False          # True when the user already has this paper


class DiscoverResponse(BaseModel):
    query: str
    source: str
    total: int                        # full PubMed result count (may be >> len(results))
    offset: int
    results: list[PaperDiscoverResult]


