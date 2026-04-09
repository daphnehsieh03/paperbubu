from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.models import (
    DailyLog,
    HeatmapDay,
    HeatmapResponse,
    Keyword,
    MeStatsResponse,
    Paper,
    PaperKeyword,
    PaperOut,
    PaperStatus,
)

router = APIRouter(prefix="/me", tags=["analytics"])


@router.get("/heatmap", response_model=HeatmapResponse)
def heatmap(session: SessionDep, user: CurrentUser) -> HeatmapResponse:
    stmt = (
        select(DailyLog.activity_date, func.count(DailyLog.id))
        .where(DailyLog.user_id == user.id)
        .group_by(DailyLog.activity_date)
        .order_by(DailyLog.activity_date)
    )
    rows = session.exec(stmt).all()
    days = [HeatmapDay(date=r[0], count=int(r[1])) for r in rows]
    return HeatmapResponse(days=days)


@router.get("/stats", response_model=MeStatsResponse)
def stats(session: SessionDep, user: CurrentUser) -> MeStatsResponse:
    total_stmt = select(func.count()).select_from(Paper).where(
        Paper.user_id == user.id,
        Paper.status == PaperStatus.completed,
    )
    total_read = int(session.exec(total_stmt).one())

    kw_count_stmt = (
        select(func.count(func.distinct(PaperKeyword.keyword_id)))
        .select_from(PaperKeyword)
        .join(Paper, Paper.id == PaperKeyword.paper_id)
        .where(Paper.user_id == user.id)
    )
    active_keyword_count = int(session.exec(kw_count_stmt).one())

    top_stmt = (
        select(Keyword.name, func.count(PaperKeyword.paper_id).label("cnt"))
        .select_from(PaperKeyword)
        .join(Keyword, Keyword.id == PaperKeyword.keyword_id)
        .join(Paper, Paper.id == PaperKeyword.paper_id)
        .where(Paper.user_id == user.id)
        .group_by(Keyword.name)
        .order_by(func.count(PaperKeyword.paper_id).desc())
        .limit(15)
    )
    top_rows = session.exec(top_stmt).all()
    top_keywords = [{"name": r[0], "count": int(r[1])} for r in top_rows]

    recent_read_stmt = (
        select(Paper)
        .where(
            Paper.user_id == user.id,
            col(Paper.completed_at).is_not(None),
        )
        .options(selectinload(Paper.keywords))
        .order_by(Paper.completed_at.desc())
        .limit(8)
    )
    recently_read = list(session.exec(recent_read_stmt).all())

    recent_open_stmt = (
        select(Paper)
        .where(
            Paper.user_id == user.id,
            col(Paper.last_opened_at).is_not(None),
        )
        .options(selectinload(Paper.keywords))
        .order_by(Paper.last_opened_at.desc())
        .limit(8)
    )
    recently_opened = list(session.exec(recent_open_stmt).all())

    return MeStatsResponse(
        total_read=total_read,
        active_keyword_count=active_keyword_count,
        top_keywords=top_keywords,
        recently_read=[PaperOut.model_validate(p) for p in recently_read],
        recently_opened=[PaperOut.model_validate(p) for p in recently_opened],
    )
