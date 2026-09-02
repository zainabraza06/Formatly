"""Exact repagination via LibreOffice (free, MPL-2.0).

Word/LibreOffice are layout engines; our parser can only *guess* page boundaries
from saved break markers. When LibreOffice is installed we get the truth: render
the DOCX to PDF (identical pagination to Word), read each PDF page's text, then
assign every graph node to its real page by matching text forward through pages.

Everything here is best-effort: any failure returns None and the caller falls back
to the marker heuristic. Enable/point to a specific binary with LIBREOFFICE_PATH.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

from app.docos.graph import DocumentGraph, Node, NodeType

# LibreOffice renders one document at a time, however many ask at once. It is
# the heaviest thing this process does, and the only one that can end it.
_CONVERTING = threading.Semaphore(1)

_CONVERT_TIMEOUT = 240  # seconds; large docs can take a while


# ── binary discovery ────────────────────────────────────────────────────────

def _soffice() -> Optional[str]:
    env = os.environ.get("LIBREOFFICE_PATH")
    if env and Path(env).exists():
        return env
    for name in ("soffice", "libreoffice", "soffice.exe"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/lib/libreoffice/program/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def libreoffice_available() -> bool:
    return _soffice() is not None


# ── conversion + extraction ─────────────────────────────────────────────────

def docx_to_pdf(data: bytes) -> Optional[Path]:
    """Public: convert DOCX bytes to a PDF file (for an exact browser preview).
    Returns the PDF path, or None if LibreOffice is unavailable or fails."""
    return _docx_to_pdf(data)


def _docx_to_pdf(data: bytes) -> Optional[Path]:
    exe = _soffice()
    if not exe:
        return None

    # One conversion at a time. LibreOffice takes a few hundred megabytes to
    # render a document, and three of them at once is what killed a container
    # with 512 MB to live in — the requests were concurrent, so the memory was
    # too. Waiting a few seconds for a PDF is a far better answer than the
    # process being killed and every request in flight dying with it.
    with _CONVERTING:
        return _convert(exe, data)


def _convert(exe: str, data: bytes) -> Optional[Path]:
    tmp = Path(tempfile.mkdtemp(prefix="docos_lo_"))
    src = tmp / "in.docx"
    src.write_bytes(data)
    profile = (tmp / "profile").as_uri()  # isolated profile → safe when headless
    try:
        subprocess.run(
            [exe, "--headless", f"-env:UserInstallation={profile}",
             "--convert-to", "pdf", "--outdir", str(tmp), str(src)],
            check=True, capture_output=True, timeout=_CONVERT_TIMEOUT,
        )
    except Exception:
        return None
    pdf = tmp / "in.pdf"
    return pdf if pdf.exists() else None


def _page_texts(pdf: Path) -> list[str]:
    """Normalised text of each PDF page, in order (single parse pass)."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer

    texts: list[str] = []
    for layout in extract_pages(str(pdf)):
        parts = [el.get_text() for el in layout if isinstance(el, LTTextContainer)]
        texts.append(_norm(" ".join(parts)))
    return texts


# ── node → page assignment ───────────────────────────────────────────────────

def repaginate(graph: DocumentGraph, data: bytes) -> Optional[int]:
    """Assign each top-level node an exact `page_index`. Returns the page count,
    or None if LibreOffice/rendering is unavailable."""
    pdf = _docx_to_pdf(data)
    if pdf is None:
        return None
    pages = _page_texts(pdf)
    if not pages:
        return None

    current = 0
    for node in graph.root.children:
        if node.type in (NodeType.HEADER, NodeType.FOOTER):
            continue  # repeat on every page; assigned below
        probe = _probe(node)
        if probe:
            found = _find_from(pages, probe, current)
            if found is not None:
                current = found
        node.metadata["page_index"] = current

    last = len(pages) - 1
    for node in graph.root.children:
        if node.type == NodeType.HEADER:
            node.metadata["page_index"] = 0
        elif node.type == NodeType.FOOTER:
            node.metadata["page_index"] = last

    page_meta = graph.root.metadata.setdefault("page", {})
    if isinstance(page_meta, dict):
        page_meta["count"] = len(pages)
        page_meta["exact"] = True
    return len(pages)


def _probe(node: Node) -> str:
    if node.type == NodeType.TABLE:
        for row in node.children:
            for cell in row.children:
                t = _norm(cell.content)
                if len(t) >= 6:
                    return t[:24]
        return ""
    t = _norm(node.content)
    if len(t) < 4:
        return ""
    return t[:24]


def _find_from(pages: list[str], probe: str, start: int) -> Optional[int]:
    for i in range(start, len(pages)):
        if probe in pages[i]:
            return i
    return None


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()
