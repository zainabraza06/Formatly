from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.schemas import (
    ChartSpec,
    ChatRequest,
    ChatResponse,
    GenerateRequest,
    GenerateResponse,
    TemplateAnalyzeResponse,
    Tone,
)
from app.services import ai
from app.services.chart_analyzer import analyze_charts
from app.services.charts import render_chart_png
from app.services.doc_pipeline import (
    create_document,
    list_recent_documents,
    load_draft,
    save_draft,
)
from app.services.export_engine import export_docx, export_excel, export_pdf
from app.services.storage import get_paths
from app.services.template_engine import analyze_template, save_template_upload

app = FastAPI(title="Formatly API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/providers/status")
def providers_status() -> dict[str, Any]:
    from app.services.router import get_router
    return get_router().status()


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> Any:
    return create_document(req)


@app.get("/documents/recent")
def recent() -> list[dict[str, Any]]:
    return list_recent_documents(10)


@app.get("/documents/{document_id}/draft")
def get_draft(document_id: str) -> dict[str, Any]:
    draft = load_draft(document_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.put("/documents/{document_id}/draft")
def put_draft(document_id: str, draft: dict[str, Any] = Body(...)) -> dict[str, str]:
    save_draft(document_id, draft)
    return {"status": "saved"}


@app.post("/documents/{document_id}/sections/{section_id}/rewrite")
def rewrite_section(document_id: str, section_id: str, tone: Tone = Body("formal")) -> dict[str, Any]:
    draft = load_draft(document_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    sections = draft.get("sections") or []
    found = False
    sec = {}
    for sec in sections:
        if sec.get("id") == section_id:
            sec["content"] = ai.rewrite_paragraph(text=sec.get("content", ""), tone=tone)
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Section not found")

    draft["sections"] = sections
    save_draft(document_id, draft)
    return {"status": "ok", "section": sec}


# ── Chart endpoints ────────────────────────────────────────────────────────────

@app.post("/documents/{document_id}/analyze-charts")
def trigger_chart_analysis(document_id: str) -> dict[str, Any]:
    """Re-run chart analysis on the saved draft and persist results."""
    draft = load_draft(document_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    from app.schemas import DocumentSection as DS
    sections = [DS(**s) for s in (draft.get("sections") or [])]
    specs = analyze_charts(sections)

    draft["suggested_charts"] = [c.model_dump() for c in specs]
    save_draft(document_id, draft)

    return {"suggested_charts": [c.model_dump() for c in specs]}


@app.post("/documents/{document_id}/charts/{index}/render")
def render_chart(document_id: str, index: int, spec: ChartSpec) -> dict[str, str]:
    """Render a single chart PNG and store it in the draft."""
    draft = load_draft(document_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    paths = get_paths()
    png   = paths.charts / f"{document_id}_{index}.png"
    render_chart_png(spec, png)

    chart_pngs  = list(draft.get("chart_pngs") or [])
    chart_specs = list(draft.get("chart_specs") or [])

    # extend lists if needed
    while len(chart_pngs) < index:
        chart_pngs.append("")
    while len(chart_specs) < index:
        chart_specs.append({})

    chart_pngs[index - 1]  = str(png)
    chart_specs[index - 1] = spec.model_dump()

    draft["chart_pngs"]  = chart_pngs
    draft["chart_specs"] = chart_specs
    save_draft(document_id, draft)

    return {"png_path": str(png), "index": str(index)}


@app.get("/documents/{document_id}/charts/{index}/image")
def get_chart_image(document_id: str, index: int) -> FileResponse:
    """Return the rendered PNG for chart at 1-based index."""
    paths = get_paths()
    png   = paths.charts / f"{document_id}_{index}.png"
    if not png.exists():
        raise HTTPException(status_code=404, detail="Chart image not found")
    return FileResponse(str(png), media_type="image/png")


# ── Export endpoints ───────────────────────────────────────────────────────────

@app.get("/documents/{document_id}/export/docx")
def download_docx(document_id: str) -> FileResponse:
    try:
        path = export_docx(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(path).name,
    )


@app.get("/documents/{document_id}/export/pdf")
def download_pdf(document_id: str) -> FileResponse:
    try:
        path = export_pdf(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found")
    return FileResponse(path, media_type="application/pdf", filename=Path(path).name)


@app.get("/documents/{document_id}/export/excel")
def download_excel(document_id: str) -> FileResponse:
    try:
        path = export_excel(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=Path(path).name,
    )


# ── Chat ───────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> Any:
    last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    msg = (
        "I can help refine your document.\n\n"
        "Try:\n"
        "- 'Rewrite the Executive Summary in a simpler tone'\n"
        "- 'Regenerate the Recommendations with 5 bullet points'\n"
        "- 'Apply a more academic style and add citations placeholders'\n\n"
        f"Your last message: {last_user}"
    )
    return {"message": msg}


# ── Templates ─────────────────────────────────────────────────────────────────

@app.post("/templates/upload", response_model=TemplateAnalyzeResponse)
async def upload_template(file: UploadFile = File(...)) -> Any:
    content  = await file.read()
    meta     = save_template_upload(
        filename=file.filename or "template",
        content=content,
        content_type=file.content_type,
    )
    analysis = analyze_template(meta["template_id"]) or {
        "template_id":     meta["template_id"],
        "filename":        meta["filename"],
        "kind":            meta["kind"],
        "summary":         "Uploaded",
        "extracted_style": {},
    }
    return analysis


@app.get("/templates/{template_id}/analyze", response_model=TemplateAnalyzeResponse)
def template_analyze(template_id: str) -> Any:
    analysis = analyze_template(template_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Template not found")
    return analysis
