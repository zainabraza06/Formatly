from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from docx import Document

from app.services.storage import get_paths, new_id, read_json, write_json


def detect_kind(filename: str, content_type: str | None = None) -> str:
    name = (filename or "").lower()
    if name.endswith(".docx"):
        return "docx"
    if name.endswith(".pdf"):
        return "pdf"
    if any(name.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
        return "image"
    if content_type:
        ct = content_type.lower()
        if "word" in ct or "officedocument" in ct:
            return "docx"
        if "pdf" in ct:
            return "pdf"
        if ct.startswith("image/"):
            return "image"
    return "unknown"


def save_template_upload(*, filename: str, content: bytes, content_type: str | None = None) -> dict[str, Any]:
    paths = get_paths()
    template_id = new_id("tpl")

    kind = detect_kind(filename, content_type)
    ext = Path(filename).suffix or (
        ".docx" if kind == "docx" else ".pdf" if kind == "pdf" else ".png" if kind == "image" else ""
    )
    stored_name = f"{template_id}{ext}"
    file_path = paths.templates / stored_name
    file_path.write_bytes(content)

    meta = {
        "template_id": template_id,
        "filename": filename,
        "kind": kind,
        "content_type": content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "stored_path": str(file_path),
    }
    write_json(paths.templates / f"{template_id}.meta.json", meta)
    return meta


def _analyze_docx(file_path: Path) -> tuple[dict[str, Any], str]:
    doc = Document(str(file_path))
    extracted: dict[str, Any] = {}

    try:
        normal = doc.styles["Normal"]
        extracted["font_name"] = normal.font.name
        if normal.font.size:
            extracted["body_pt"] = int(normal.font.size.pt)
    except Exception:
        pass

    try:
        h1 = doc.styles["Heading 1"]
        if h1.font.size:
            extracted["heading1_pt"] = int(h1.font.size.pt)
        if h1.font.bold is not None:
            extracted["heading_bold"] = bool(h1.font.bold)
        if h1.font.name:
            extracted["font_name"] = extracted.get("font_name") or h1.font.name
    except Exception:
        pass

    try:
        section = doc.sections[0]
        extracted["margin_in"] = float(section.left_margin.inches)
    except Exception:
        pass

    summary = "DOCX template analyzed: extracted base font, heading sizing, and margins."
    return extracted, summary


def _analyze_pdf(file_path: Path) -> tuple[dict[str, Any], str]:
    extracted: dict[str, Any] = {}
    summary = "PDF template uploaded. For best cloning fidelity, upload DOCX templates (full style extraction is supported for DOCX)."
    try:
        from pdfminer.high_level import extract_text

        text = extract_text(str(file_path), maxpages=1) or ""
        extracted["sample_text"] = text.strip()[:600]
        summary = "PDF template analyzed: extracted sample text from first page (style cloning is limited for PDFs)."
    except Exception:
        pass
    return extracted, summary


def _analyze_image(file_path: Path) -> tuple[dict[str, Any], str]:
    extracted: dict[str, Any] = {}
    summary = "Image template uploaded. Style cloning from images is limited; DOCX templates provide full style cloning."
    # Pillow is intentionally not required (Python 3.14 compatibility). Keep analysis minimal.
    return extracted, summary


def analyze_template(template_id: str) -> dict[str, Any] | None:
    paths = get_paths()
    meta = read_json(paths.templates / f"{template_id}.meta.json")
    if not meta:
        return None

    file_path = Path(meta["stored_path"])
    kind = meta.get("kind", "unknown")

    if kind == "docx":
        extracted, summary = _analyze_docx(file_path)
    elif kind == "pdf":
        extracted, summary = _analyze_pdf(file_path)
    elif kind == "image":
        extracted, summary = _analyze_image(file_path)
    else:
        extracted, summary = {}, "Unknown template type."

    analysis = {
        "template_id": template_id,
        "filename": meta.get("filename", ""),
        "kind": kind,
        "summary": summary,
        "extracted_style": extracted,
    }

    write_json(paths.templates / f"{template_id}.analysis.json", analysis)
    return analysis


def get_template_style(template_id: str) -> dict[str, Any] | None:
    paths = get_paths()
    analysis = read_json(paths.templates / f"{template_id}.analysis.json")
    if not analysis:
        analysis = analyze_template(template_id)
    if not analysis:
        return None
    return analysis.get("extracted_style") or None
