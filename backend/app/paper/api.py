"""Paper/report generation API, mounted at /paper.

    POST /paper/generate  raw material          → fully-styled spec JSON
    POST /paper/render    spec JSON             → .docx download
    POST /paper/compose   raw material          → .docx download (generate + render)
    GET  /paper/styles    available stylesheets
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.docos.auth import get_current_user
from app.docos.auth.store import User
from app.paper.generator import PaperGenerationError, generate_paper
from app.paper.renderer import render_paper
from app.paper.schema import PaperSpec
from app.paper.styles import DEFAULT_STYLE, list_styles
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
def styles() -> list[dict[str, str]]:
    return list_styles()


@router.post("/generate")
def generate(req: GenerateRequest, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Raw material → fully-styled spec JSON (every block carries explicit formatting)."""
    try:
        spec, provider = generate_paper(
            raw_text=req.raw_text, style=req.style, doc_kind=req.doc_kind,
            code=req.code, results=req.results,
            reference_example=req.reference_example, instructions=req.instructions,
            title_hint=req.title_hint, authors=req.authors or None,
        )
    except PaperGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"provider": provider, "spec": spec.to_dict()}


@router.post("/render")
def render(spec: dict[str, Any] = Body(...), style: Optional[str] = None,
           user: User = Depends(get_current_user)) -> FileResponse:
    """Execute a spec JSON and return the .docx."""
    try:
        parsed = resolve(PaperSpec.model_validate(spec), style)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid paper spec: {exc}")

    out = get_paths().documents / f"{new_id('paper')}.docx"
    render_paper(parsed, out)
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
        )
    except PaperGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    out = get_paths().documents / f"{new_id('paper')}.docx"
    render_paper(spec, out)
    return FileResponse(str(out), media_type=_DOCX_MIME,
                        filename=f"{_safe(spec.meta.title)}.docx")


def _safe(name: str) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in (name or "document"))
    return (keep.strip() or "document")[:60]
