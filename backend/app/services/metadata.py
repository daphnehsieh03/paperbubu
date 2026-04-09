import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote as urlquote

import httpx

from app.services.pdf import (
    ARXIV_ABS_PATTERN,
    ARXIV_CLASSIC_PATTERN,
    DOI_PATTERN,
)

ATOM = "{http://www.w3.org/2005/Atom}"


def parse_ids_from_url(url: str) -> tuple[str | None, str | None]:
    u = url.strip()
    doi_m = DOI_PATTERN.search(u)
    if doi_m:
        return doi_m.group(1), None
    for pat in (ARXIV_ABS_PATTERN, ARXIV_CLASSIC_PATTERN):
        m = pat.search(u)
        if m:
            return None, m.group(1)
    if "doi.org/" in u:
        tail = u.split("doi.org/", 1)[-1]
        tail = tail.split("?", 1)[0].strip("/")
        if tail.startswith("10."):
            return tail, None
    # Nature / Nature Portfolio: /articles/{id} — DOI is 10.1038/{id}
    nature_m = re.search(r"nature\.com/articles/([^/?#]+)", u, re.I)
    if nature_m:
        article_id = nature_m.group(1).strip("/").split("/")[0]
        if article_id and re.match(r"^[a-z0-9][a-z0-9._-]*$", article_id, re.I):
            return f"10.1038/{article_id}", None
    return None, None


async def fetch_crossref(doi: str) -> dict[str, Any]:
    doi_enc = urlquote(doi)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"https://api.crossref.org/works/{doi_enc}",
            headers={"User-Agent": "Papertrail/1.0 (mailto:dev@local)"},
        )
        r.raise_for_status()
        data = r.json()["message"]
    title_list = data.get("title") or []
    title = title_list[0] if title_list else "Unknown title"
    authors: list[str] = []
    for a in data.get("author") or []:
        given = a.get("given", "")
        family = a.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)
    journal = None
    container = data.get("container-title")
    if isinstance(container, list) and container:
        journal = container[0]
    elif isinstance(container, str):
        journal = container
    pub_date = None
    for key in ("published-print", "published-online", "created"):
        part = data.get(key)
        if part and "date-parts" in part and part["date-parts"]:
            parts = part["date-parts"][0]
            if len(parts) >= 3:
                pub_date = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) >= 1:
                pub_date = f"{parts[0]:04d}"
            break
    return {
        "title": title,
        "authors": authors,
        "journal": journal,
        "published_date": pub_date,
        "doi": data.get("DOI") or doi,
        "arxiv_id": None,
    }


async def fetch_arxiv(arxiv_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            "http://export.arxiv.org/api/query",
            params={"id_list": arxiv_id},
        )
        r.raise_for_status()
    root = ET.fromstring(r.text)
    entry = root.find(f"{ATOM}entry")
    if entry is None:
        raise ValueError("arXiv entry not found")
    title_el = entry.find(f"{ATOM}title")
    title = (title_el.text or "").replace("\n", " ").strip() if title_el is not None else "Unknown"
    authors: list[str] = []
    for author in entry.findall(f"{ATOM}author"):
        name_el = author.find(f"{ATOM}name")
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())
    published_el = entry.find(f"{ATOM}published")
    pub = published_el.text[:10] if published_el is not None and published_el.text else None
    id_el = entry.find(f"{ATOM}id")
    doi = None
    aid = arxiv_id
    if id_el is not None and id_el.text:
        m = re.search(r"arxiv\.org/abs/([^?#]+)", id_el.text, re.I)
        if m:
            aid = m.group(1).rstrip("/")
    return {
        "title": title,
        "authors": authors,
        "journal": "arXiv",
        "published_date": pub,
        "doi": doi,
        "arxiv_id": aid,
    }


async def resolve_metadata(doi: str | None, arxiv_id: str | None) -> dict[str, Any]:
    if doi:
        return await fetch_crossref(doi)
    if arxiv_id:
        return await fetch_arxiv(arxiv_id)
    raise ValueError("No DOI or arXiv id to resolve")
