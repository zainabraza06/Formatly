from __future__ import annotations

from pathlib import Path

from app.schemas import ChartSpec, DocumentSection
from app.services.doc_pipeline import load_draft
from app.services.docx_engine import build_docx
from app.services.excel_engine import build_excel
from app.services.pdf_engine import build_pdf
from app.services.storage import get_paths


def export_docx(document_id: str) -> Path:
    draft = load_draft(document_id)
    if not draft:
        raise FileNotFoundError("Draft not found")

    paths = get_paths()
    out   = paths.documents / f"{document_id}.docx"

    sections    = [DocumentSection(**s) for s in (draft.get("sections") or [])]
    chart_pngs  = [Path(p) for p in (draft.get("chart_pngs") or [])]
    chart_specs = [ChartSpec(**c) for c in (draft.get("chart_specs") or [])]

    return build_docx(
        out_path=out,
        title=draft.get("title") or "Untitled Document",
        outline=draft.get("outline") or [],
        sections=sections,
        style_preset=draft.get("style_preset") or "business",
        extracted_rules=draft.get("extracted_rules") or {},
        chart_specs=chart_specs or None,
        chart_pngs=chart_pngs or None,
        include_title_page=bool(draft.get("include_title_page", True)),
        include_toc=bool(draft.get("include_toc", True)),
    )


def export_pdf(document_id: str) -> Path:
    draft = load_draft(document_id)
    if not draft:
        raise FileNotFoundError("Draft not found")

    paths = get_paths()
    out   = paths.documents / f"{document_id}.pdf"

    sections    = [DocumentSection(**s) for s in (draft.get("sections") or [])]
    chart_pngs  = [Path(p) for p in (draft.get("chart_pngs") or [])]
    chart_specs = [ChartSpec(**c) for c in (draft.get("chart_specs") or [])]

    return build_pdf(
        out_path=out,
        title=draft.get("title") or "Untitled Document",
        outline=draft.get("outline") or [],
        sections=sections,
        style_preset=draft.get("style_preset") or "business",
        extracted_rules=draft.get("extracted_rules") or {},
        chart_specs=chart_specs or None,
        chart_pngs=chart_pngs or None,
        include_title_page=bool(draft.get("include_title_page", True)),
        include_toc=bool(draft.get("include_toc", True)),
    )


def export_excel(document_id: str) -> Path:
    draft = load_draft(document_id)
    if not draft:
        raise FileNotFoundError("Draft not found")

    paths = get_paths()
    out   = paths.documents / f"{document_id}.xlsx"

    sections    = [DocumentSection(**s) for s in (draft.get("sections") or [])]
    chart_specs = [ChartSpec(**c) for c in (draft.get("chart_specs") or [])]

    # fall back to suggested_charts when no rendered specs are stored
    if not chart_specs:
        chart_specs = [ChartSpec(**c) for c in (draft.get("suggested_charts") or [])]

    return build_excel(
        out_path=out,
        title=draft.get("title") or "Untitled Document",
        outline=draft.get("outline") or [],
        sections=sections,
        chart_specs=chart_specs or None,
    )
