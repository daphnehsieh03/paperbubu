"""Fetch PDFs from open-access sources (arXiv, PMC) and persist them locally.

Supported sources
─────────────────
  arXiv   — any paper whose arxiv_id is a bare arXiv identifier (e.g. "2401.12345")
             PDF URL: https://arxiv.org/pdf/{arxiv_id}

  PMC     — any paper imported from PubMed whose arxiv_id field holds "pmid:{pmid}"
             Flow: PMID → NCBI elink → PMCID → PMC PDF URL

Papers behind a paywall cannot be fetched automatically; the user must
download the PDF manually and upload it via the drag-and-drop interface.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import httpx

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ARXIV_PDF_TEMPLATE = "https://arxiv.org/pdf/{arxiv_id}"
PMC_PDF_TEMPLATE = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf/"

# ── public entry point ─────────────────────────────────────────────────────


async def fetch_and_store_pdf(
    *,
    arxiv_id: str | None,
    upload_dir: str,
    api_key: str = "",
) -> str:
    """Download a PDF for the given paper identifiers and save it locally.

    Returns the absolute path to the saved file.

    Raises
    ------
    ValueError   — no fetchable source (neither open-access arXiv nor PMC)
    ValueError   — PMC has no full-text copy for this PMID
    httpx.HTTPStatusError — the remote server returned an error
    ValueError   — the response was not a PDF (e.g. a paywall HTML page)
    """
    pdf_url = await _resolve_pdf_url(arxiv_id=arxiv_id, api_key=api_key)
    return await _download_to_disk(pdf_url, upload_dir)


# ── URL resolution ─────────────────────────────────────────────────────────


async def _resolve_pdf_url(*, arxiv_id: str | None, api_key: str) -> str:
    """Work out which URL to download the PDF from."""

    if arxiv_id and arxiv_id.startswith("pmid:"):
        pmid = arxiv_id.removeprefix("pmid:")
        return await _pmc_pdf_url(pmid, api_key=api_key)

    if arxiv_id:
        # Strip version suffix if present (e.g. "2401.12345v2" → "2401.12345")
        clean = arxiv_id.split("v")[0] if arxiv_id[-2] == "v" and arxiv_id[-1].isdigit() else arxiv_id
        return ARXIV_PDF_TEMPLATE.format(arxiv_id=clean)

    raise ValueError(
        "No fetchable source: paper has no arXiv ID and was not imported from PubMed. "
        "Please download the PDF manually and upload it."
    )


async def _pmc_pdf_url(pmid: str, *, api_key: str) -> str:
    """Convert a PubMed PMID to a PMC full-text PDF URL via NCBI elink.

    Raises ValueError if no open-access PMC record exists for this PMID.
    """
    params: dict[str, Any] = {
        "dbfrom": "pubmed",
        "db": "pmc",
        "id": pmid,
        "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{EUTILS_BASE}/elink.fcgi", params=params)
        r.raise_for_status()

    data = r.json()

    for linkset in data.get("linksets", []):
        for linksetdb in linkset.get("linksetdbs", []):
            if linksetdb.get("dbto") == "pmc":
                links = linksetdb.get("links", [])
                if links:
                    pmcid = str(links[0])
                    return PMC_PDF_TEMPLATE.format(pmcid=pmcid)

    raise ValueError(
        f"PMID {pmid} has no open-access full text in PubMed Central. "
        "The paper may be behind a paywall — please download and upload the PDF manually."
    )


# ── download ───────────────────────────────────────────────────────────────


async def _download_to_disk(url: str, upload_dir: str) -> str:
    """Fetch a PDF from *url*, validate it, and write it to *upload_dir*.

    Returns the absolute path of the saved file.
    """
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    dest = Path(upload_dir) / f"{uuid.uuid4().hex}.pdf"

    async with httpx.AsyncClient(
        timeout=60.0,
        follow_redirects=True,
        headers={"User-Agent": "paperbubu/1.0 (open-access research tool)"},
    ) as client:
        r = await client.get(url)
        r.raise_for_status()

    # Validate: real PDFs start with the %PDF- magic bytes.
    # A paywall page or error HTML would fail this check.
    content = r.content
    if not content.startswith(b"%PDF-"):
        raise ValueError(
            "The server did not return a valid PDF. "
            "The paper may require institutional access — please download manually."
        )

    dest.write_bytes(content)
    return str(dest.resolve())
