"""PubMed E-utilities client for paper discovery.

Two-step flow:
  1. esearch  — query → ranked list of PMIDs
  2. efetch   — PMIDs → full article XML → parsed metadata

Rate limits (NCBI):
  - No API key : 3 requests/second
  - With API key: 10 requests/second
Set PUBMED_API_KEY in .env to raise the limit.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_URL_TEMPLATE = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
PMC_URL_TEMPLATE = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/"
DOI_URL_TEMPLATE = "https://doi.org/{doi}"

# ── XML namespace shortcuts ────────────────────────────────────────────────


def _text(el: ET.Element | None) -> str:
    """Return stripped text of an element, or empty string."""
    return (el.text or "").strip() if el is not None else ""


def _find_text(parent: ET.Element, *path: str) -> str:
    """Walk a tag path and return text of the last element found."""
    node = parent
    for tag in path:
        node = node.find(tag)  # type: ignore[assignment]
        if node is None:
            return ""
    return _text(node)


# ── Public API ─────────────────────────────────────────────────────────────


async def search_pubmed(
    query: str,
    *,
    limit: int = 20,
    offset: int = 0,
    api_key: str = "",
) -> tuple[list[str], int]:
    """Return (pmids, total_count) for the given query.

    PMIDs are sorted by PubMed relevance (best-match algorithm).
    total_count is the full result set size (not just this page).
    """
    params: dict[str, Any] = {
        "db": "pubmed",
        "term": query,
        "retmax": limit,
        "retstart": offset,
        "sort": "relevance",
        "retmode": "json",
        "usehistory": "n",
    }
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{EUTILS_BASE}/esearch.fcgi", params=params)
        r.raise_for_status()

    data = r.json()
    result = data.get("esearchresult", {})
    pmids: list[str] = result.get("idlist", [])
    total: int = int(result.get("count", 0))
    return pmids, total


async def fetch_pubmed_details(
    pmids: list[str],
    *,
    api_key: str = "",
) -> list[dict[str, Any]]:
    """Fetch full article metadata for a list of PMIDs.

    Returns a list of normalised dicts — one per PMID — in the same order
    as the input list. Missing articles are silently dropped.
    """
    if not pmids:
        return []

    params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    }
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(f"{EUTILS_BASE}/efetch.fcgi", params=params)
        r.raise_for_status()

    root = ET.fromstring(r.text)
    results: list[dict[str, Any]] = []

    for article in root.findall("PubmedArticle"):
        parsed = _parse_article(article)
        if parsed:
            results.append(parsed)

    return results


async def fetch_single_pmid(pmid: str, *, api_key: str = "") -> dict[str, Any] | None:
    """Convenience wrapper: fetch metadata for exactly one PMID."""
    records = await fetch_pubmed_details([pmid], api_key=api_key)
    return records[0] if records else None


# ── XML parsing ────────────────────────────────────────────────────────────


def _parse_article(article: ET.Element) -> dict[str, Any] | None:
    citation = article.find("MedlineCitation")
    if citation is None:
        return None

    pmid_el = citation.find("PMID")
    pmid = _text(pmid_el)
    if not pmid:
        return None

    art = citation.find("Article")
    if art is None:
        return None

    title = _find_text(art, "ArticleTitle")

    # Abstract — may have multiple structured AbstractText sections
    abstract_parts: list[str] = []
    abstract_el = art.find("Abstract")
    if abstract_el is not None:
        for at in abstract_el.findall("AbstractText"):
            label = at.get("Label", "")
            text = (at.text or "").strip()
            if text:
                abstract_parts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abstract_parts) or None

    # Authors
    authors: list[str] = []
    author_list = art.find("AuthorList")
    if author_list is not None:
        for author in author_list.findall("Author"):
            last = _find_text(author, "LastName")
            fore = _find_text(author, "ForeName")
            initials = _find_text(author, "Initials")
            collective = _find_text(author, "CollectiveName")
            if collective:
                authors.append(collective)
            elif last:
                name = f"{fore} {last}".strip() if fore else f"{initials} {last}".strip() if initials else last
                authors.append(name)

    # Journal
    journal_el = art.find("Journal")
    journal_title: str | None = None
    if journal_el is not None:
        jt = journal_el.find("Title") or journal_el.find("ISOAbbreviation")
        journal_title = _text(jt) or None

    # Publication date — prefer MedlineDate > Year/Month
    pub_date: str | None = None
    if journal_el is not None:
        ji = journal_el.find("JournalIssue")
        if ji is not None:
            pd = ji.find("PubDate")
            if pd is not None:
                medline = pd.find("MedlineDate")
                if medline is not None:
                    pub_date = _text(medline)[:4] or None  # "2024 Jan-Feb" → "2024"
                else:
                    year = _text(pd.find("Year"))
                    month = _text(pd.find("Month"))
                    pub_date = f"{year}-{month}" if month else year or None

    # DOI and PMC ID — check ELocationID first, then PubmedData/ArticleIdList
    doi: str | None = None
    pmc_id: str | None = None

    for eloc in art.findall("ELocationID"):
        if eloc.get("EIdType") == "doi":
            doi = _text(eloc) or None
            break

    pubmed_data = article.find("PubmedData")
    if pubmed_data is not None:
        for aid in pubmed_data.findall(".//ArticleId"):
            id_type = aid.get("IdType")
            val = _text(aid) or None
            if id_type == "doi" and doi is None:
                doi = val
            elif id_type == "pmc" and val:
                # stored as "PMC1234567" — strip prefix for the URL template
                pmc_id = val.lstrip("PMCpmc")

    pmc_url = PMC_URL_TEMPLATE.format(pmcid=pmc_id) if pmc_id else None
    doi_url = DOI_URL_TEMPLATE.format(doi=doi) if doi else None

    return {
        "pmid": pmid,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "journal": journal_title,
        "published_date": pub_date,
        "doi": doi,
        "doi_url": doi_url,
        "pmc_url": pmc_url,
        "pubmed_url": PUBMED_URL_TEMPLATE.format(pmid=pmid),
    }
