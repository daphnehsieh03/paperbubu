from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Union

from fastapi import APIRouter, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.models import DailyLog, Keyword, Paper, PaperKeyword, PaperStatus
from app.models import CreatePaperUrlBody, PaperOut, PaperPatch
from app.services.metadata import parse_ids_from_url, resolve_metadata
from app.services.paper_helpers import authors_to_str, build_search_document, safe_unlink_file
from app.services.pdf import extract_ids_from_pdf

router = APIRouter(prefix="/papers", tags=["papers"])


def _ensure_upload_dir() -> Path:
    p = Path(settings.upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _create_paper_core(
    session: Session,
    user_id: int,
    *,
    title: str,
    authors: str,
    doi: str | None,
    arxiv_id: str | None,
    file_path: str | None,
) -> Paper:
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
    paper = session.exec(stmt).one()
    return paper


@router.get("", response_model=list[PaperOut])
def list_papers(
    session: SessionDep,
    user: CurrentUser,
    status_filter: Annotated[PaperStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[Paper]:
    stmt = select(Paper).where(Paper.user_id == user.id).options(selectinload(Paper.keywords))
    if status_filter is not None:
        stmt = stmt.where(Paper.status == status_filter)
    if q and q.strip():
        stmt = stmt.where(col(Paper.search_document).contains(q.strip().lower()))
    stmt = stmt.order_by(Paper.created_at.desc()).offset(offset).limit(limit)
    return list(session.exec(stmt).all())


@router.post("", response_model=Union[PaperOut, list[PaperOut]])
async def create_paper(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
) -> Paper | list[Paper]:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        body = CreatePaperUrlBody.model_validate(await request.json())
        doi, arxiv_id = parse_ids_from_url(body.url)
        if not doi and not arxiv_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not parse DOI or arXiv id from URL",
            )
        try:
            meta = await resolve_metadata(doi, arxiv_id)
        except Exception:
            meta = {
                "title": "Imported paper",
                "authors": [],
                "doi": doi,
                "arxiv_id": arxiv_id,
            }
        authors = authors_to_str(meta.get("authors") or [])
        paper = _create_paper_core(
            session,
            user.id,
            title=meta.get("title") or "Untitled",
            authors=authors,
            doi=meta.get("doi") or doi,
            arxiv_id=meta.get("arxiv_id") or arxiv_id,
            file_path=None,
        )
        return paper

    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Use application/json with {url} or multipart/form-data with file field(s)",
        )

    form = await request.form()
    files = form.getlist("file")
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file(s) in multipart form (use field name 'file')")

    upload_dir = _ensure_upload_dir()
    created: list[Paper] = []

    for uf in files:
        if not hasattr(uf, "read"):
            continue
        upload: UploadFile = uf  # type: ignore[assignment]
        suffix = Path(upload.filename or "paper.pdf").suffix or ".pdf"
        name = f"{uuid.uuid4().hex}{suffix}"
        dest = upload_dir / name
        data = await upload.read()
        dest.write_bytes(data)

        doi_pdf, arxiv_pdf = extract_ids_from_pdf(dest)
        title = Path(upload.filename or "paper").stem
        authors = ""
        doi, arxiv_id = doi_pdf, arxiv_pdf
        if doi or arxiv_id:
            try:
                meta = await resolve_metadata(doi, arxiv_id)
                title = meta.get("title") or title
                authors = authors_to_str(meta.get("authors") or [])
                doi = meta.get("doi") or doi
                arxiv_id = meta.get("arxiv_id") or arxiv_id
            except Exception:
                pass

        paper = _create_paper_core(
            session,
            user.id,
            title=title,
            authors=authors,
            doi=doi,
            arxiv_id=arxiv_id,
            file_path=str(dest.resolve()),
        )
        created.append(paper)

    if not created:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid files uploaded")

    if len(created) == 1:
        return created[0]
    return created


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int, session: SessionDep, user: CurrentUser) -> Paper:
    stmt = (
        select(Paper)
        .where(Paper.id == paper_id, Paper.user_id == user.id)
        .options(selectinload(Paper.keywords))
    )
    paper = session.exec(stmt).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return paper


@router.post("/{paper_id}/open", response_model=PaperOut)
def mark_opened(paper_id: int, session: SessionDep, user: CurrentUser) -> Paper:
    stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == user.id).options(selectinload(Paper.keywords))
    paper = session.exec(stmt).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    paper.last_opened_at = datetime.utcnow()
    session.add(paper)
    session.commit()
    session.refresh(paper)
    return paper


def _set_keywords(session: Session, paper: Paper, names: list[str]) -> None:
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


@router.patch("/{paper_id}", response_model=PaperOut)
def patch_paper(
    paper_id: int,
    body: PaperPatch,
    session: SessionDep,
    user: CurrentUser,
) -> Paper:
    stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == user.id).options(selectinload(Paper.keywords))
    paper = session.exec(stmt).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    old_status = paper.status
    if body.title is not None:
        paper.title = body.title
    if body.authors is not None:
        paper.authors = body.authors
    if body.status is not None:
        paper.status = body.status
        if body.status == PaperStatus.completed and old_status != PaperStatus.completed:
            paper.completed_at = datetime.utcnow()
            session.add(
                DailyLog(
                    paper_id=paper.id,
                    user_id=user.id,
                    activity_date=paper.completed_at.date(),
                )
            )
    if body.keyword_names is not None:
        _set_keywords(session, paper, body.keyword_names)
    elif body.title is not None or body.authors is not None:
        kw_rows = session.exec(
            select(Keyword.name)
            .join(PaperKeyword, PaperKeyword.keyword_id == Keyword.id)
            .where(PaperKeyword.paper_id == paper.id)
        ).all()
        paper.search_document = build_search_document(
            paper.title,
            paper.authors,
            paper.doi,
            paper.arxiv_id,
            list(kw_rows),
        )

    session.add(paper)
    session.commit()
    session.refresh(paper)
    stmt = select(Paper).where(Paper.id == paper.id).options(selectinload(Paper.keywords))
    return session.exec(stmt).one()


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_paper(paper_id: int, session: SessionDep, user: CurrentUser) -> Response:
    stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == user.id)
    paper = session.exec(stmt).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    for row in session.exec(select(DailyLog).where(DailyLog.paper_id == paper_id)).all():
        session.delete(row)
    for row in session.exec(select(PaperKeyword).where(PaperKeyword.paper_id == paper_id)).all():
        session.delete(row)

    safe_unlink_file(paper.file_path)
    session.delete(paper)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
