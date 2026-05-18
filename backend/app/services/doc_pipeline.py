from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.schemas import DocumentSection, GenerateRequest
from app.services import ai
from app.services.charts import render_chart_png
from app.services.rules import extract_rules
from app.services.storage import get_paths, new_id, read_json, write_json
from app.services.template_engine import get_template_style


PIPELINE = [
    "User Prompt",
    "Intent Extraction",
    "Document Planning",
    "Content Generation",
    "Formatting Engine",
    "Export Engine",
]


def create_document(req: GenerateRequest) -> dict[str, Any]:
    paths = get_paths()
    document_id = new_id("doc")

    extracted_rules = extract_rules(req.formatting_instructions)
    template_style = get_template_style(req.template_id) if req.template_id else None

    pipeline = [
        {"name": PIPELINE[0], "status": "done", "detail": "Prompt received"},
        {"name": PIPELINE[1], "status": "done", "detail": f"Extracted {len(extracted_rules)} formatting rules"},
        {"name": PIPELINE[2], "status": "done", "detail": "Outline planned"},
        {"name": PIPELINE[3], "status": "done", "detail": "Sections generated"},
        {"name": PIPELINE[4], "status": "done", "detail": "Formatting prepared"},
        {"name": PIPELINE[5], "status": "pending", "detail": "Ready for export"},
    ]

    doc_struct = ai.generate_structured_document(
        prompt=req.prompt,
        formatting_rules=extracted_rules,
        style_preset=req.style_preset,
        tone=req.tone,
        template_style=template_style,
    )

    title = doc_struct.get("title") or "Untitled Document"
    outline = doc_struct.get("outline") or []

    sections = []
    for i, s in enumerate(doc_struct.get("sections") or []):
        sec_id = f"sec_{i+1}"
        sections.append(DocumentSection(id=sec_id, heading=s.get("heading", "Section"), content=s.get("content", "")))

    chart_pngs: list[str] = []
    if req.include_charts or extracted_rules.get("include_charts"):
        for i, spec in enumerate(req.charts or []):
            png = paths.charts / f"{document_id}_{i+1}.png"
            render_chart_png(spec, png)
            chart_pngs.append(str(png))

    draft = {
        "document_id": document_id,
        "title": title,
        "outline": outline,
        "sections": [s.model_dump() for s in sections],
        "extracted_rules": extracted_rules,
        "style_preset": req.style_preset,
        "tone": req.tone,
        "template_id": req.template_id,
        "template_style": template_style or {},
        "include_title_page": req.include_title_page,
        "include_toc": req.include_toc,
        "chart_pngs": chart_pngs,
        "created_at": None,
    }

    write_json(paths.documents / f"{document_id}.draft.json", draft)

    return {
        "document_id": document_id,
        "title": title,
        "outline": outline,
        "sections": [s.model_dump() for s in sections],
        "extracted_rules": extracted_rules,
        "pipeline": pipeline,
    }


def load_draft(document_id: str) -> Optional[dict[str, Any]]:
    paths = get_paths()
    return read_json(paths.documents / f"{document_id}.draft.json")


def save_draft(document_id: str, draft: dict[str, Any]) -> None:
    paths = get_paths()
    write_json(paths.documents / f"{document_id}.draft.json", draft)


def list_recent_documents(limit: int = 10) -> list[dict[str, Any]]:
    paths = get_paths()
    drafts = sorted(paths.documents.glob("*.draft.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in drafts[:limit]:
        d = read_json(p) or {}
        out.append({"document_id": d.get("document_id"), "title": d.get("title"), "style_preset": d.get("style_preset")})
    return out
