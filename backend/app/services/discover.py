"""Query helpers for the paper discovery feature.

These functions read from the Paper table to answer the question
'what does this user already have?' — pure data access, no business rules.
They live here so the discover router stays free of direct DB calls.
"""

from __future__ import annotations

from sqlmodel import Session, col, select

from app.models import Paper


def doi_set_for_user(session: Session, user_id: int) -> set[str]:
    """Return the lowercased DOIs the user already has in their library."""
    rows = session.exec(
        select(Paper.doi).where(Paper.user_id == user_id, col(Paper.doi).is_not(None))
    ).all()
    return {doi.lower() for doi in rows if doi}


def pmid_set_for_user(session: Session, user_id: int) -> set[str]:
    """Return the PMIDs the user already has in their library.

    PubMed papers are stored with arxiv_id = 'pmid:{pmid}' to avoid
    adding a new column.  This query strips the prefix so callers get
    bare PMID strings they can compare against PubMed search results.
    """
    rows = session.exec(
        select(Paper.arxiv_id).where(
            Paper.user_id == user_id,
            col(Paper.arxiv_id).like("pmid:%"),
        )
    ).all()
    return {row.removeprefix("pmid:") for row in rows if row}
