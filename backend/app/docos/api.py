"""FastAPI router for DocOS, mounted at /docos."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from app.docos.events import get_hub
from app.docos.service import get_service

router = APIRouter(prefix="/docos", tags=["docos"])


@router.post("/import")
async def import_document(file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read()
    title = (file.filename or "document").rsplit(".", 1)[0]
    try:
        return get_service().import_docx(data, title=title)
    except Exception as exc:  # parse failure
        raise HTTPException(status_code=400, detail=f"failed to parse DOCX: {exc}")


@router.get("/{doc_id}")
def get_document(doc_id: str) -> dict[str, Any]:
    try:
        return get_service().get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")


@router.get("/{doc_id}/history")
def history(doc_id: str) -> list[dict[str, Any]]:
    try:
        return get_service().history(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")


@router.get("/{doc_id}/diff")
def diff(doc_id: str, a: int, b: int) -> dict[str, Any]:
    try:
        return get_service().diff(doc_id, a, b)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{doc_id}/command")
async def command(doc_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
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
        result = await get_service().run_command(doc_id, cmd, emit)
    except KeyError:
        raise HTTPException(status_code=404, detail="document not found")
    return {**result, "events": collected}


@router.websocket("/ws/{doc_id}")
async def ws(websocket: WebSocket, doc_id: str) -> None:
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
                await get_service().run_command(doc_id, cmd, emit)
            except KeyError:
                await websocket.send_json({"event": "error", "payload": {"detail": "document not found"}})
    except WebSocketDisconnect:
        await hub.disconnect(doc_id, websocket)
    except Exception:
        await hub.disconnect(doc_id, websocket)
