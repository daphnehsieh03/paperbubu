from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated, Union

from fastapi import APIRouter, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.models import CreatePaperUrlBody, Keyword, Paper, PaperKeyword, PaperOut, PaperPatch, PaperStatus
from app.services.metadata import parse_ids_from_url, resolve_metadata
from app.services.paper_helpers import authors_to_str, build_search_document
from app.services.papers import (
    create_paper,
    delete_paper,
    mark_paper_completed,
    mark_paper_opened,
    set_keywords,
)
from app.services.pdf import extract_ids_from_pdf
from app.services.pdf_fetch import fetch_and_store_pdf

router = APIRouter(prefix="/papers", tags=["papers"])


def _ensure_upload_dir() -> Path:
    p = Path(settings.upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


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
async def create_paper_endpoint(
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
            meta = {"title": "Imported paper", "authors": [], "doi": doi, "arxiv_id": arxiv_id}
        authors = authors_to_str(meta.get("authors") or [])
        return create_paper(
            session,
            user.id,
            title=meta.get("title") or "Untitled",
            authors=authors,
            doi=meta.get("doi") or doi,
            arxiv_id=meta.get("arxiv_id") or arxiv_id,
            file_path=None,
        )

    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Use application/json with {url} or multipart/form-data with file field(s)",
        )

    form = await request.form()
    files = form.getlist("file")
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file(s) in multipart form (use field name 'file')",
        )

    upload_dir = _ensure_upload_dir()
    created: list[Paper] = []

    for uf in files:
        if not hasattr(uf, "read"):
            continue
        upload: UploadFile = uf  # type: ignore[assignment]
        suffix = Path(upload.filename or "paper.pdf").suffix or ".pdf"
        dest = upload_dir / f"{uuid.uuid4().hex}{suffix}"
        dest.write_bytes(await upload.read())

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

        created.append(create_paper(
            session,
            user.id,
            title=title,
            authors=authors,
            doi=doi,
            arxiv_id=arxiv_id,
            file_path=str(dest.resolve()),
        ))

    if not created:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid files uploaded")

    return created[0] if len(created) == 1 else created


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
    stmt = (
        select(Paper)
        .where(Paper.id == paper_id, Paper.user_id == user.id)
        .options(selectinload(Paper.keywords))
    )
    paper = session.exec(stmt).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return mark_paper_opened(session, paper)


@router.patch("/{paper_id}", response_model=PaperOut)
def patch_paper(
    paper_id: int,
    body: PaperPatch,
    session: SessionDep,
    user: CurrentUser,
) -> Paper:
    stmt = (
        select(Paper)
        .where(Paper.id == paper_id, Paper.user_id == user.id)
        .options(selectinload(Paper.keywords))
    )
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
            mark_paper_completed(session, paper, user.id)

    if body.keyword_names is not None:
        set_keywords(session, paper, body.keyword_names)
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
    return session.exec(
        select(Paper).where(Paper.id == paper.id).options(selectinload(Paper.keywords))
    ).one()


@router.post("/{paper_id}/fetch-pdf", response_model=PaperOut)
async def fetch_paper_pdf(paper_id: int, session: SessionDep, user: CurrentUser) -> Paper:
    """Auto-download the PDF for an open-access paper and attach it to the library entry.

    Works for:
      - arXiv papers  (arxiv_id is a bare arXiv identifier)
      - PubMed papers that have a PMC full-text copy (arxiv_id = "pmid:{pmid}")

    Returns 409 if a PDF is already attached.
    Returns 422 if the paper has no fetchable source.
    Returns 502 if the remote server fails or returns a non-PDF response.
    """
    stmt = (
        select(Paper)
        .where(Paper.id == paper_id, Paper.user_id == user.id)
        .options(selectinload(Paper.keywords))
    )
    paper = session.exec(stmt).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    if paper.file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A PDF is already attached to this paper. Delete it first or upload a replacement.",
        )

    try:
        file_path = await fetch_and_store_pdf(
            arxiv_id=paper.arxiv_id,
            upload_dir=settings.upload_dir,
            api_key=settings.pubmed_api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch PDF: {exc}",
        )

    paper.file_path = file_path
    session.add(paper)
    session.commit()
    return session.exec(
        select(Paper).where(Paper.id == paper.id).options(selectinload(Paper.keywords))
    ).one()


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_paper_endpoint(paper_id: int, session: SessionDep, user: CurrentUser) -> Response:
    paper = session.exec(select(Paper).where(Paper.id == paper_id, Paper.user_id == user.id)).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    delete_paper(session, paper)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
