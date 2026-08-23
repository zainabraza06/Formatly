"""FastAPI router for DocOS, mounted at /docos. All routes require auth and are
scoped to the authenticated user."""
from __future__ import annotations

from typing import Any

from fastapi.responses import FileResponse
from fastapi import (
    APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, UploadFile, WebSocket,
    WebSocketDisconnect,
)

from app.docos.auth import get_current_user, user_from_token
from app.docos.auth.store import User
from app.docos.events import get_hub
from app.docos.service import get_service

router = APIRouter(prefix="/docos", tags=["docos"])


@router.get("")
def list_documents(user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    return get_service().list_documents(owner_id=user.id)


async def _read_after_import(doc_id: str, owner_id: str) -> None:
    """Read a freshly imported document through once, in the background.

    The import answers straight away — nobody should wait on a model to see
    their own document — and the reading follows, announcing itself page by page
    to whoever is watching the document. By the time an instruction arrives, the
    assistant has usually read the thing it is being asked about.
    """
    hub = get_hub()

    async def emit(message: dict[str, Any]) -> None:
        await hub.broadcast(doc_id, message)

    try:
        await get_service().read_document(doc_id, emit, owner_id=owner_id)
    except Exception as exc:  # a reading is an improvement, never a requirement
        await emit({"event": "reading_finished",
                    "payload": {"read": 0, "warnings": [str(exc)]}})


@router.post("/import")
async def import_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    data = await file.read()
    title = (file.filename or "document").rsplit(".", 1)[0]
    try:
        result = get_service().import_docx(data, title=title, owner_id=user.id)
    except Exception as exc:  # parse failure
        raise HTTPException(status_code=400, detail=f"failed to parse DOCX: {exc}")

    background.add_task(_read_after_import, result["document_id"], user.id)
    return result


@router.post("/import-spec")
def import_spec(background: BackgroundTasks,
                payload: dict[str, Any] = Body(...),
                user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Open a composed document in the editor, straight from its spec.

    The alternative is rendering it to .docx and importing that, which loses
    every distinction the file format cannot carry.
    """
    from app.paper.schema import PaperSpec

    raw = payload.get("spec", payload)
    try:
        spec = PaperSpec.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid paper spec: {exc}")
    if not spec.blocks:
        raise HTTPException(status_code=422, detail="paper spec has no content blocks")

    title = str(payload.get("title") or spec.meta.title or "Untitled")
    try:
        result = get_service().import_spec(spec, title=title, owner_id=user.id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"could not build the document: {exc}")

    # A composed document is read too: the editor should know it as well as one
    # that arrived as a file.
    background.add_task(_read_after_import, result["document_id"], user.id)
    return result


@router.get("/{doc_id}")
def get_document(doc_id: str, user: User = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return get_service().get_document(doc_id, owner_id=user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")


@router.get("/{doc_id}/exact.pdf")
def exact_view(doc_id: str, user: User = Depends(get_current_user)) -> FileResponse:
    """The document as a real layout engine renders it.

    The editor lays out with HTML and CSS, which comes close but cannot
    reproduce Word's line breaking or pagination. This writes the *current*
    graph — edits included — back to DOCX and lets LibreOffice lay it out, so
    the exact view is of the document as it stands rather than as it arrived.
    """
    from app.docos.export import graph_to_docx_bytes
    from app.docos.parser.paginator import docx_to_pdf, libreoffice_available

    if not libreoffice_available():
        raise HTTPException(status_code=503, detail="the exact view needs LibreOffice")

    try:
        graph = get_service().current_graph(doc_id, owner_id=user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=404, detail="document not found")

    pdf = docx_to_pdf(graph_to_docx_bytes(graph))
    if pdf is None:
        raise HTTPException(status_code=503, detail="could not render the exact view")
    return FileResponse(str(pdf), media_type="application/pdf",
                        filename=f"{doc_id}.pdf")


@router.delete("/{doc_id}")
def delete_document(doc_id: str, user: User = Depends(get_current_user)) -> dict[str, bool]:
    try:
        return {"deleted": get_service().delete_document(doc_id, owner_id=user.id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")


@router.get("/{doc_id}/brief")
def brief(doc_id: str, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """What the document is: its kind, sections, inventory and conventions.

    Read from the graph each time rather than stored, so it cannot fall behind
    the document it describes.
    """
    try:
        return get_service().brief(doc_id, owner_id=user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")


@router.post("/{doc_id}/read")
async def read(doc_id: str, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Read the document through once, page by page, and keep what it says."""
    hub = get_hub()
    collected: list[dict[str, Any]] = []

    async def emit(msg: dict[str, Any]) -> None:
        collected.append(msg)
        await hub.broadcast(doc_id, msg)

    try:
        result = await get_service().read_document(doc_id, emit, owner_id=user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")
    return {**result, "events": collected}


@router.get("/{doc_id}/history")
def history(doc_id: str, user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    try:
        return get_service().history(doc_id, owner_id=user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")


@router.get("/{doc_id}/diff")
def diff(doc_id: str, a: int, b: int, user: User = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return get_service().diff(doc_id, a, b, owner_id=user.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")


@router.post("/{doc_id}/command")
async def command(
    doc_id: str,
    body: dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Run a command over REST. Events are also broadcast to any WS watchers."""
    cmd = (body.get("command") or "").strip()
    if not cmd:
        raise HTTPException(status_code=422, detail="command is required")
    hub = get_hub()
    collected: list[dict[str, Any]] = []

    async def emit(msg: dict[str, Any]) -> None:
        collected.append(msg)
        await hub.broadcast(doc_id, msg)

    try:
        result = await get_service().run_command(doc_id, cmd, emit, owner_id=user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")
    return {**result, "events": collected}


@router.websocket("/ws/{doc_id}")
async def ws(websocket: WebSocket, doc_id: str) -> None:
    # WebSocket can't send Authorization headers from the browser — auth via ?token=
    user = user_from_token(websocket.query_params.get("token"))
    if user is None:
        await websocket.close(code=4401)  # unauthorized
        return

    hub = get_hub()
    await hub.connect(doc_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            cmd = (data.get("command") or "").strip()
            if not cmd:
                await websocket.send_json({"event": "error", "payload": {"detail": "empty command"}})
                continue

            async def emit(msg: dict[str, Any]) -> None:
                await hub.broadcast(doc_id, msg)

            try:
                await get_service().run_command(doc_id, cmd, emit, owner_id=user.id)
            except KeyError:
                await websocket.send_json({"event": "error", "payload": {"detail": "document not found"}})
            except PermissionError:
                await websocket.send_json({"event": "error", "payload": {"detail": "not your document"}})
    except WebSocketDisconnect:
        await hub.disconnect(doc_id, websocket)
    except Exception:
        await hub.disconnect(doc_id, websocket)
