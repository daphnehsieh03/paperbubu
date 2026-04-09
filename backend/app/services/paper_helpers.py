import json
from pathlib import Path

from app.models import Keyword, Paper


def authors_to_str(authors: list[str]) -> str:
    return json.dumps(authors) if authors else ""


def build_search_document(
    title: str,
    authors: str,
    doi: str | None,
    arxiv_id: str | None,
    keyword_names: list[str] | None = None,
) -> str:
    parts = [title, authors or "", doi or "", arxiv_id or ""]
    if keyword_names:
        parts.extend(keyword_names)
    return " ".join(p for p in parts if p).lower()


def keyword_names_for_paper(paper: Paper) -> list[str]:
    return [k.name for k in (paper.keywords or [])]


def refresh_search_document(session, paper: Paper) -> None:
    names = keyword_names_for_paper(paper)
    paper.search_document = build_search_document(
        paper.title,
        paper.authors,
        paper.doi,
        paper.arxiv_id,
        names,
    )
    session.add(paper)


def safe_unlink_file(path: str | None) -> None:
    if not path:
        return
    p = Path(path)
    if p.is_file():
        p.unlink()
