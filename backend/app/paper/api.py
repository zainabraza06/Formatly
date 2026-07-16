"""Paper/report generation API, mounted at /paper.

    POST /paper/generate  raw material          → fully-styled spec JSON
    POST /paper/render    spec JSON             → .docx download
    POST /paper/compose   raw material          → .docx download (generate + render)
    GET  /paper/styles    available stylesheets
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.docos.auth import get_current_user
from app.docos.auth.store import User
from app.paper.generator import PaperGenerationError, generate_paper
from app.paper.renderer import render_paper
from app.paper.schema import PaperSpec
from app.paper.styles import DEFAULT_STYLE, get_stylesheet, list_styles, resolve_style
from app.paper.styles.base import StyleSheet
from app.paper.styles.extract import derive_stylesheet_from_docx
from app.paper.styles.store import get_style_store
from app.paper.stylesheet import resolve
from app.services.storage import get_paths, new_id

router = APIRouter(prefix="/paper", tags=["paper"])

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class GenerateRequest(BaseModel):
    raw_text: str = Field(min_length=1)
    style: str = DEFAULT_STYLE          # ieee | apa | acm | report | …
    doc_kind: str = "paper"             # paper | report | thesis | …
    code: Optional[str] = None
    results: Optional[str] = None
    reference_example: Optional[str] = None
    instructions: Optional[str] = None
    title_hint: Optional[str] = None
    authors: list[dict[str, str]] = Field(default_factory=list)


@router.get("/styles")
def styles(user: User = Depends(get_current_user)) -> list[dict[str, str]]:
    """Built-in styles plus this user's custom styles."""
    return list_styles(owner_id=user.id)


@router.get("/styles/{style_id}")
def get_style(style_id: str, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Full stylesheet definition — useful as a starting point for a custom style."""
    sheet = resolve_style(style_id, user.id)
    return sheet.model_dump(mode="json")


@router.post("/styles")
def create_style(sheet: dict[str, Any] = Body(...),
                 user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Define a custom style from a stylesheet JSON (no code change needed)."""
    try:
        parsed = StyleSheet.model_validate(sheet)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid stylesheet: {exc}")
    if not parsed.name.strip():
        raise HTTPException(status_code=422, detail="stylesheet needs a name")
    saved = get_style_store().save(user.id, parsed)
    return saved.model_dump(mode="json")


@router.post("/styles/from-docx")
async def style_from_docx(
    file: UploadFile = File(...),
    name: str = Form(...),
    base: str = Form(DEFAULT_STYLE),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Learn a custom style from a reference DOCX: fonts, sizes, alignment and page
    geometry are read from the sample; anything it doesn't reveal falls back to `base`."""
    data = await file.read()
    try:
        derived = derive_stylesheet_from_docx(
            data, name=name, base=get_stylesheet(base),
            source_filename=file.filename or "reference.docx",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"could not read reference DOCX: {exc}")
    saved = get_style_store().save(user.id, derived)
    return saved.model_dump(mode="json")


@router.delete("/styles/{style_id}")
def delete_style(style_id: str, user: User = Depends(get_current_user)) -> dict[str, bool]:
    if not get_style_store().delete(style_id, user.id):
        raise HTTPException(status_code=404, detail="custom style not found")
    return {"deleted": True}


@router.post("/generate")
def generate(req: GenerateRequest, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Raw material → fully-styled spec JSON (every block carries explicit formatting)."""
    try:
        spec, provider = generate_paper(
            raw_text=req.raw_text, style=req.style, doc_kind=req.doc_kind,
            code=req.code, results=req.results,
            reference_example=req.reference_example, instructions=req.instructions,
            title_hint=req.title_hint, authors=req.authors or None,
            owner_id=user.id,
        )
    except PaperGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"provider": provider, "spec": spec.to_dict()}


@router.post("/render")
def render(spec: dict[str, Any] = Body(...), style: Optional[str] = None,
           user: User = Depends(get_current_user)) -> FileResponse:
    """Execute a spec JSON and return the .docx."""
    try:
        parsed = resolve(PaperSpec.model_validate(spec), style, user.id)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid paper spec: {exc}")

    out = get_paths().documents / f"{new_id('paper')}.docx"
    render_paper(parsed, out, owner_id=user.id)
    return FileResponse(str(out), media_type=_DOCX_MIME,
                        filename=f"{_safe(parsed.meta.title)}.docx")


@router.post("/compose")
def compose(req: GenerateRequest, user: User = Depends(get_current_user)) -> FileResponse:
    """Raw material → .docx in one call."""
    try:
        spec, _provider = generate_paper(
            raw_text=req.raw_text, style=req.style, doc_kind=req.doc_kind,
            code=req.code, results=req.results,
            reference_example=req.reference_example, instructions=req.instructions,
            title_hint=req.title_hint, authors=req.authors or None,
            owner_id=user.id,
        )
    except PaperGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    out = get_paths().documents / f"{new_id('paper')}.docx"
    render_paper(spec, out, owner_id=user.id)
    return FileResponse(str(out), media_type=_DOCX_MIME,
                        filename=f"{_safe(spec.meta.title)}.docx")


def _safe(name: str) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in (name or "document"))
    return (keep.strip() or "document")[:60]
