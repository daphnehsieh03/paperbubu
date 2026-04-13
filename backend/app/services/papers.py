"""Business logic for paper lifecycle: creation, updates, keyword management, deletion."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models import DailyLog, Keyword, Paper, PaperKeyword, PaperStatus
from app.services.paper_helpers import build_search_document, safe_unlink_file


def create_paper(
    session: Session,
    user_id: int,
    *,
    title: str,
    authors: str,
    doi: str | None,
    arxiv_id: str | None,
    file_path: str | None,
) -> Paper:
    """Create and persist a new paper, returning it with keywords loaded."""
    paper = Paper(
        title=title,
        authors=authors,
        doi=doi,
        arxiv_id=arxiv_id,
        status=PaperStatus.to_read,
        file_path=file_path,
        user_id=user_id,
        search_document=build_search_document(title, authors, doi, arxiv_id, None),
    )
    session.add(paper)
    session.commit()
    session.refresh(paper)
    stmt = select(Paper).where(Paper.id == paper.id).options(selectinload(Paper.keywords))
    return session.exec(stmt).one()


def set_keywords(session: Session, paper: Paper, names: list[str]) -> None:
    """Replace a paper's keywords and rebuild its search document.

    Normalises names to lowercase, deduplicates, and upserts Keyword rows.
    """
    for row in session.exec(select(PaperKeyword).where(PaperKeyword.paper_id == paper.id)).all():
        session.delete(row)
    session.flush()

    norm: list[str] = []
    for raw in names:
        name = raw.strip().lower()
        if not name:
            continue
        kw = session.exec(select(Keyword).where(Keyword.name == name)).first()
        if kw is None:
            kw = Keyword(name=name)
            session.add(kw)
            session.flush()
        session.add(PaperKeyword(paper_id=paper.id, keyword_id=kw.id))
        norm.append(name)

    paper.search_document = build_search_document(
        paper.title,
        paper.authors,
        paper.doi,
        paper.arxiv_id,
        norm,
    )


def mark_paper_completed(session: Session, paper: Paper, user_id: int) -> None:
    """Record that a paper was completed and write the activity log entry."""
    paper.completed_at = datetime.utcnow()
    session.add(
        DailyLog(
            paper_id=paper.id,
            user_id=user_id,
            activity_date=paper.completed_at.date(),
        )
    )


def mark_paper_opened(session: Session, paper: Paper) -> Paper:
    """Stamp last_opened_at and persist the change."""
    paper.last_opened_at = datetime.utcnow()
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper


def delete_paper(session: Session, paper: Paper) -> None:
    """Remove a paper and all its related rows, plus the file on disk if present."""
    for row in session.exec(select(DailyLog).where(DailyLog.paper_id == paper.id)).all():
        session.delete(row)
    for row in session.exec(select(PaperKeyword).where(PaperKeyword.paper_id == paper.id)).all():
        session.delete(row)
    safe_unlink_file(paper.file_path)
    session.delete(paper)
    session.commit()
