"""FastAPI router for DocOS, mounted at /docos. All routes require auth and are
scoped to the authenticated user."""
from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter, Body, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect,
)

from app.docos.auth import get_current_user, user_from_token
from app.docos.auth.store import User
from app.docos.events import get_hub
from app.docos.service import get_service

router = APIRouter(prefix="/docos", tags=["docos"])


@router.get("")
def list_documents(user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    return get_service().list_documents(owner_id=user.id)


@router.post("/import")
async def import_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    data = await file.read()
    title = (file.filename or "document").rsplit(".", 1)[0]
    try:
        return get_service().import_docx(data, title=title, owner_id=user.id)
    except Exception as exc:  # parse failure
        raise HTTPException(status_code=400, detail=f"failed to parse DOCX: {exc}")


@router.get("/{doc_id}")
def get_document(doc_id: str, user: User = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return get_service().get_document(doc_id, owner_id=user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="not your document")


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
