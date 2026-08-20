"""Paper/report generation API, mounted at /paper.

    POST /paper/generate  raw material          → fully-styled spec JSON
    POST /paper/render    spec JSON             → .docx download
    POST /paper/compose   raw material          → .docx download (generate + render)
    GET  /paper/styles    available stylesheets
"""
from __future__ import annotations

import anyio
import anyio.to_thread
import threading
from typing import Any, Callable, Optional, TypeVar

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from app.docos.auth import get_current_user
from app.docos.auth.store import User
from app.paper.generator import PaperGenerationError, generate_paper
from app.paper.prompt import DEFAULT_DEPTH, DEPTHS
from app.paper.refine import InstructionRefinementError, refine_instructions
from app.paper.renderer import render_paper
from app.paper.schema import PaperSpec
from app.paper.styles import DEFAULT_STYLE, list_styles, resolve_style
from app.paper.styles.base import StyleSheet
from app.paper.styles.store import get_style_store
from app.paper.stylesheet import resolve
from app.services.router import GenerationCancelled
from app.services.storage import get_paths, new_id

router = APIRouter(prefix="/paper", tags=["paper"])

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class Attachment(BaseModel):
    """Any extra material the user wants considered, under their own label:
    measurements, survey responses, a transcript, source code, citations…"""
    label: str = ""
    content: str = ""


class RefineInstructionsRequest(BaseModel):
    """What the user typed, plus enough context to refine it usefully."""
    instructions: str = Field(min_length=1)
    raw_text: str = ""
    doc_kind: str = "document"
    style: str = DEFAULT_STYLE
    # A previous attempt and what was wrong with it, so a retry is a correction
    # rather than another roll of the dice.
    previous: Optional[str] = None
    feedback: Optional[str] = None


class GenerateRequest(BaseModel):
    raw_text: str = Field(min_length=1)
    style: str = DEFAULT_STYLE          # ieee | apa | acm | report | <custom id> …
    doc_kind: str = "document"          # paper | report | memo | proposal | …
    depth: str = DEFAULT_DEPTH          # brief | standard | detailed
    attachments: list[Attachment] = Field(default_factory=list)
    reference_example: Optional[str] = None
    instructions: Optional[str] = None
    title_hint: Optional[str] = None
    authors: list[dict[str, str]] = Field(default_factory=list)

    def attachment_dicts(self) -> list[dict[str, str]]:
        return [a.model_dump() for a in self.attachments]


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


@router.delete("/styles/{style_id}")
def delete_style(style_id: str, user: User = Depends(get_current_user)) -> dict[str, bool]:
    if not get_style_store().delete(style_id, user.id):
        raise HTTPException(status_code=404, detail="custom style not found")
    return {"deleted": True}



_T = TypeVar("_T")

# 499 is nginx's "client closed request". There is no standard code for it, and
# it matters that this is not logged as a 5xx: nothing went wrong.
_CLIENT_CLOSED = 499

# How often to ask whether the caller is still there. Frequent enough that a
# cancelled run stops promptly, cheap enough to ignore.
_DISCONNECT_POLL_SECONDS = 0.5


async def _run_cancellable(request: Request, work: Callable[[threading.Event], _T]) -> _T:
    """Run blocking `work` in a worker thread, abandoning it if the caller goes.

    Generation costs money for as long as it runs, so a browser that has given
    up — Stop pressed, tab closed, navigation — should not leave a request
    burning tokens for another two minutes. `work` receives an Event that is set
    the moment the client disconnects; the router closes its transport on it.
    """
    cancel = threading.Event()
    outcome: dict[str, Any] = {}

    def runner() -> None:
        # The result is carried out by hand rather than raised through the task
        # group: anyio wraps anything that escapes one in an ExceptionGroup, and
        # the endpoint wants to catch GenerationCancelled itself.
        try:
            outcome["value"] = work(cancel)
        except BaseException as exc:       # noqa: BLE001 — re-raised verbatim below
            outcome["error"] = exc

    async def watch() -> None:
        try:
            while not cancel.is_set():
                if await request.is_disconnected():
                    cancel.set()
                    return
                await anyio.sleep(_DISCONNECT_POLL_SECONDS)
        except Exception:
            pass    # never let the watcher be the reason a request fails

    async with anyio.create_task_group() as tg:
        tg.start_soon(watch)
        try:
            await anyio.to_thread.run_sync(runner)
        finally:
            cancel.set()      # stop the watcher whichever way the work ended
            tg.cancel_scope.cancel()

    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


@router.post("/generate")
async def generate(req: GenerateRequest, request: Request,
                   user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Raw material → fully-styled spec JSON (every block carries explicit formatting)."""
    def work(cancel: threading.Event):
        return generate_paper(
            raw_text=req.raw_text, style=req.style, doc_kind=req.doc_kind,
            depth=req.depth, attachments=req.attachment_dicts(),
            reference_example=req.reference_example, instructions=req.instructions,
            title_hint=req.title_hint, authors=req.authors or None,
            owner_id=user.id, cancel=cancel,
        )

    try:
        spec, provider = await _run_cancellable(request, work)
    except GenerationCancelled:
        raise HTTPException(status_code=_CLIENT_CLOSED, detail="cancelled by the client")
    except PaperGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    doc_id = new_id('paper')
    spec_dict = spec.to_dict()
    
    from app.services.storage import write_json, get_paths
    write_json(get_paths().documents / f"{doc_id}.spec.json", spec_dict)
    
    return {"provider": provider, "spec": spec_dict, "document_id": doc_id}


def _parse_spec(spec: Any, style: Optional[str], owner_id: str) -> PaperSpec:
    """Validate a spec request body, refusing one with nothing in it.

    Every PaperSpec field carries a default, so `{}` — or any JSON that simply
    is not a spec — validates cleanly into an "Untitled" document with no
    content. Rendering that returned 200 and a blank .docx, which reads as a
    silent success: the caller gets a file and no hint that their body was
    wrong. A spec with no blocks is a client error, so say so.
    """
    if not isinstance(spec, dict) or not spec:
        raise HTTPException(status_code=422,
                            detail="paper spec must be a non-empty JSON object")
    try:
        parsed = PaperSpec.model_validate(spec)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"invalid paper spec: {exc}")

    if not parsed.blocks:
        raise HTTPException(
            status_code=422,
            detail="paper spec has no content blocks — nothing to render. "
                   "Send the object returned by /paper/generate, or its \"spec\" field.")
    try:
        return resolve(parsed, style, owner_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"could not apply style: {exc}")


@router.post("/render")
def render(spec: dict[str, Any] = Body(...), style: Optional[str] = None,
           user: User = Depends(get_current_user)) -> FileResponse:
    """Execute a spec JSON and return the .docx."""
    parsed = _parse_spec(spec, style, user.id)

    out = get_paths().documents / f"{new_id('paper')}.docx"
    render_paper(parsed, out, owner_id=user.id)
    return FileResponse(str(out), media_type=_DOCX_MIME,
                        filename=f"{_safe(parsed.meta.title)}.docx")


@router.post("/preview")
def preview(spec: dict[str, Any] = Body(...), style: Optional[str] = None,
            user: User = Depends(get_current_user)) -> FileResponse:
    """Render the real DOCX and return it as a PDF, for a pixel-exact browser
    preview — the actual document, not an HTML approximation. Needs LibreOffice."""
    from app.docos.parser.paginator import docx_to_pdf, libreoffice_available

    parsed = _parse_spec(spec, style, user.id)

    if not libreoffice_available():
        raise HTTPException(status_code=503, detail="exact preview needs LibreOffice")

    out = get_paths().documents / f"{new_id('preview')}.docx"
    render_paper(parsed, out, owner_id=user.id)
    pdf = docx_to_pdf(out.read_bytes())
    if pdf is None:
        raise HTTPException(status_code=503, detail="could not render the exact preview")
    return FileResponse(str(pdf), media_type="application/pdf",
                        filename=f"{_safe(parsed.meta.title)}.pdf")


@router.post("/compose")
async def compose(req: GenerateRequest, request: Request,
                  user: User = Depends(get_current_user)) -> FileResponse:
    """Raw material → .docx in one call."""
    def work(cancel: threading.Event):
        return generate_paper(
            raw_text=req.raw_text, style=req.style, doc_kind=req.doc_kind,
            depth=req.depth, attachments=req.attachment_dicts(),
            reference_example=req.reference_example, instructions=req.instructions,
            title_hint=req.title_hint, authors=req.authors or None,
            owner_id=user.id, cancel=cancel,
        )

    try:
        spec, _provider = await _run_cancellable(request, work)
    except GenerationCancelled:
        raise HTTPException(status_code=_CLIENT_CLOSED, detail="cancelled by the client")
    except PaperGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    doc_id = new_id('paper')
    from app.services.storage import write_json, get_paths
    write_json(get_paths().documents / f"{doc_id}.spec.json", spec.to_dict())

    out = get_paths().documents / f"{doc_id}.docx"
    render_paper(spec, out, owner_id=user.id)
    return FileResponse(str(out), media_type=_DOCX_MIME,
                        filename=f"{_safe(spec.meta.title)}.docx")


def _safe(name: str) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in (name or "document"))
    return (keep.strip() or "document")[:60]


@router.post("/instructions/refine")
async def refine(req: RefineInstructionsRequest, request: Request,
                 user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Turn a loose instruction into one the writer can actually act on.

    Nothing is generated here and nothing is saved — the caller decides whether
    to keep the result, send feedback and try again, or ignore it entirely.
    """
    def work(cancel: threading.Event):
        return refine_instructions(
            instructions=req.instructions, raw_text=req.raw_text,
            doc_kind=req.doc_kind, style=req.style,
            previous=req.previous, feedback=req.feedback, cancel=cancel,
        )

    try:
        refined, provider = await _run_cancellable(request, work)
    except GenerationCancelled:
        raise HTTPException(status_code=_CLIENT_CLOSED, detail="cancelled by the client")
    except InstructionRefinementError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"provider": provider, **refined.model_dump()}


@router.get("/recent")
def recent_papers(user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    """List recently generated paper specs."""
    from app.services.storage import get_paths, read_json
    paths = get_paths()
    specs = sorted(
        paths.documents.glob("*.spec.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out = []
    for p in specs[:20]:
        d = read_json(p) or {}
        meta = d.get("meta", {})
        out.append({
            "document_id": p.name.replace(".spec.json", ""),
            "title": meta.get("title", "Untitled Document"),
            "style_preset": meta.get("style", "ieee"),
        })
    return out


@router.get("/{document_id}/export/docx")
def export_paper_docx(document_id: str, user: User = Depends(get_current_user)) -> FileResponse:
    from app.services.storage import get_paths, read_json
    paths = get_paths()
    spec = read_json(paths.documents / f"{document_id}.spec.json")
    if not spec:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    parsed = _parse_spec(spec, None, user.id)
    out = paths.documents / f"{document_id}.docx"
    render_paper(parsed, out, owner_id=user.id)
    
    return FileResponse(str(out), media_type=_DOCX_MIME,
                        filename=f"{_safe(parsed.meta.title)}.docx")


@router.get("/{document_id}/export/pdf")
def export_paper_pdf(document_id: str, user: User = Depends(get_current_user)) -> FileResponse:
    from app.services.storage import get_paths, read_json
    from app.docos.parser.paginator import docx_to_pdf, libreoffice_available
    
    paths = get_paths()
    spec = read_json(paths.documents / f"{document_id}.spec.json")
    if not spec:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    if not libreoffice_available():
        raise HTTPException(status_code=503, detail="PDF export needs LibreOffice")
        
    parsed = _parse_spec(spec, None, user.id)
    out = paths.documents / f"{document_id}.docx"
    render_paper(parsed, out, owner_id=user.id)
    
    pdf = docx_to_pdf(out.read_bytes())
    if pdf is None:
        raise HTTPException(status_code=503, detail="Could not render PDF")
        
    return FileResponse(str(pdf), media_type="application/pdf",
                        filename=f"{_safe(parsed.meta.title)}.pdf")

