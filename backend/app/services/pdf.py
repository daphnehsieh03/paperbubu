import re
from pathlib import Path

import fitz  # PyMuPDF

DOI_PATTERN = re.compile(
    r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b",
    re.IGNORECASE,
)
ARXIV_ABS_PATTERN = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
ARXIV_CLASSIC_PATTERN = re.compile(
    r"arxiv\.org/(?:abs|pdf)/([a-z-]+(?:\.[A-Za-z-]+)?/\d{7})(?:v\d+)?",
    re.IGNORECASE,
)
ARXIV_INLINE_PATTERN = re.compile(
    r"arXiv:\s*(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)


def extract_ids_from_pdf(path: Path, max_pages: int = 3) -> tuple[str | None, str | None]:
    """Return (doi, arxiv_id) first match wins per type."""
    doc = fitz.open(path)
    text_parts: list[str] = []
    for i in range(min(max_pages, doc.page_count)):
        text_parts.append(doc.load_page(i).get_text() or "")
    doc.close()
    blob = "\n".join(text_parts)

    doi_match = DOI_PATTERN.search(blob)
    doi = doi_match.group(1) if doi_match else None

    arxiv_id: str | None = None
    for pattern in (ARXIV_ABS_PATTERN, ARXIV_CLASSIC_PATTERN, ARXIV_INLINE_PATTERN):
        m = pattern.search(blob)
        if m:
            arxiv_id = m.group(1)
            break

    return doi, arxiv_id
