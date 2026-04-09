"""SQLModel table models and Pydantic API payloads in one module (SQLModel-friendly)."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field as PydanticField
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
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperKeyword(SQLModel, table=True):
    paper_id: int = Field(foreign_key="paper.id", primary_key=True)
    keyword_id: int = Field(foreign_key="keyword.id", primary_key=True)


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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = PydanticField(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreatePaperUrlBody(BaseModel):
    url: str


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


class PaperPatch(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    status: Optional[PaperStatus] = None
    keyword_names: Optional[list[str]] = None


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
