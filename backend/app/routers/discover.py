"""Paper discovery via PubMed E-utilities.

Endpoints
─────────
GET  /discover
    Search PubMed for papers matching a query.
    Does NOT write to the database.
    Marks results already in the user's library (in_library=True).

POST /discover/import
    Fetch full metadata for one PMID and add it to the user's library.
    Reuses the existing create_paper service so the same business rules apply
    (search_document built, keywords empty, status=to_read).

Design rationale
────────────────
Discovery is intentionally separated from the papers router because it has a
completely different data source (PubMed, not the local DB) and a different
contract (results are transient, not persisted by the search call itself).
The import step is the explicit user action that bridges discovery → library.
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.models import (
    DiscoverResponse,
    PaperDiscoverResult,
    PaperOut,
    PubMedImportBody,
    Paper,
)
from app.services.discover import doi_set_for_user, pmid_set_for_user
from app.services.paper_helpers import authors_to_str
from app.services.papers import create_paper
from app.services.pubmed import fetch_single_pmid, search_pubmed, fetch_pubmed_details

router = APIRouter(prefix="/discover", tags=["discover"])


# ── helpers ────────────────────────────────────────────────────────────────


def _build_discover_result(
    record: dict,
    *,
    in_library: bool = False,
) -> PaperDiscoverResult:
    return PaperDiscoverResult(
        source="pubmed",
        external_id=record["pmid"],
        title=record.get("title") or "Untitled",
        authors=record.get("authors") or [],
        abstract=record.get("abstract"),
        journal=record.get("journal"),
        published_date=record.get("published_date"),
        doi=record.get("doi"),
        doi_url=record.get("doi_url"),
        pmc_url=record.get("pmc_url"),
        pubmed_url=record.get("pubmed_url"),
        in_library=in_library,
    )


# ── routes ─────────────────────────────────────────────────────────────────


@router.get("", response_model=DiscoverResponse)
async def search_papers(
    session: SessionDep,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=1, description="Search query, e.g. 'KRAS oncogene'")],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DiscoverResponse:
    """Search PubMed for papers matching the query.

    Results are ranked by PubMed's relevance algorithm (best-match).
    Each result carries an ``in_library`` flag so the UI can show
    which papers the user has already added.

    This endpoint never writes to the database.
    """
    q = q.strip()

    # 1. Get ranked PMIDs from PubMed esearch
    try:
        pmids, total = await search_pubmed(
            q,
            limit=limit,
            offset=offset,
            api_key=settings.pubmed_api_key,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PubMed search failed: {exc}",
        )

    if not pmids:
        return DiscoverResponse(
            query=q,
            source="pubmed",
            total=total,
            offset=offset,
            results=[],
        )

    # 2. Fetch full metadata for those PMIDs
    try:
        records = await fetch_pubmed_details(pmids, api_key=settings.pubmed_api_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PubMed fetch failed: {exc}",
        )

    # 3. Check which papers the user already has (by DOI or PMID tag)
    user_dois = doi_set_for_user(session, user.id)
    user_pmids = pmid_set_for_user(session, user.id)

    results: list[PaperDiscoverResult] = []
    for record in records:
        doi = (record.get("doi") or "").lower()
        pmid = record.get("pmid", "")
        in_library = (doi and doi in user_dois) or (pmid in user_pmids)
        results.append(_build_discover_result(record, in_library=in_library))

    return DiscoverResponse(
        query=q,
        source="pubmed",
        total=total,
        offset=offset,
        results=results,
    )


@router.post("/import", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
async def import_paper(
    body: PubMedImportBody,
    session: SessionDep,
    user: CurrentUser,
) -> Paper:
    """Import a discovered PubMed paper into the user's library.

    Fetches full metadata for the given PMID from PubMed, then calls the
    same ``create_paper`` service used by the regular papers router.
    The paper is saved with:
      - status = to_read
      - arxiv_id set to "pmid:{pmid}" so the library-check in GET /discover
        can detect it without a separate DB column
      - file_path = None (no PDF yet; user can upload separately)
    """
    pmid = body.pmid.strip()

    # Guard: already in library?
    existing_pmids = pmid_set_for_user(session, user.id)
    if pmid in existing_pmids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This paper is already in your library",
        )

    # Fetch metadata from PubMed
    try:
        record = await fetch_single_pmid(pmid, api_key=settings.pubmed_api_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PubMed fetch failed: {exc}",
        )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PMID {pmid} not found on PubMed",
        )

    # Guard: DOI already in library?
    doi = record.get("doi")
    if doi:
        user_dois = doi_set_for_user(session, user.id)
        if doi.lower() in user_dois:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A paper with this DOI is already in your library",
            )

    authors_str = authors_to_str(record.get("authors") or [])

    paper = create_paper(
        session,
        user.id,
        title=record.get("title") or "Untitled",
        authors=authors_str,
        doi=doi,
        # Store PMID as arxiv_id with a prefix so it's queryable
        # without adding a new DB column.
        arxiv_id=f"pmid:{pmid}",
        file_path=None,
    )
    return paper
