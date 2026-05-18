from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.schemas import (
    ChatRequest,
    ChatResponse,
    GenerateRequest,
    GenerateResponse,
    TemplateAnalyzeResponse,
    Tone,
)
from app.services import ai
from app.services.doc_pipeline import create_document, list_recent_documents, load_draft, save_draft
from app.services.export_engine import export_docx, export_pdf
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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> Any:
    # Minimal assistant: echoes last user message with guidance.
    last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    msg = (
        "I can help refine your document.\n\n"
        "Try:\n"
        "- ‘Rewrite the Executive Summary in a simpler tone’\n"
        "- ‘Regenerate the Recommendations with 5 bullet points’\n"
        "- ‘Apply a more academic style and add citations placeholders’\n\n"
        f"Your last message: {last_user}"
    )
    return {"message": msg}


@app.post("/templates/upload", response_model=TemplateAnalyzeResponse)
async def upload_template(file: UploadFile = File(...)) -> Any:
    content = await file.read()
    meta = save_template_upload(filename=file.filename or "template", content=content, content_type=file.content_type)
    analysis = analyze_template(meta["template_id"]) or {
        "template_id": meta["template_id"],
        "filename": meta["filename"],
        "kind": meta["kind"],
        "summary": "Uploaded",
        "extracted_style": {},
    }
    return analysis


@app.get("/templates/{template_id}/analyze", response_model=TemplateAnalyzeResponse)
def template_analyze(template_id: str) -> Any:
    analysis = analyze_template(template_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Template not found")
    return analysis


@app.get("/documents/{document_id}/export/docx")
def download_docx(document_id: str) -> FileResponse:
    try:
        path = export_docx(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=Path(path).name)


@app.get("/documents/{document_id}/export/pdf")
def download_pdf(document_id: str) -> FileResponse:
    try:
        path = export_pdf(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Draft not found")
    return FileResponse(path, media_type="application/pdf", filename=Path(path).name)
