"""WebSocket connection hub. Fans out execution events to every client watching
a document, so multiple viewers animate in sync."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class EventHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, doc_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(doc_id, set()).add(ws)

    async def disconnect(self, doc_id: str, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(doc_id)
            if room:
                room.discard(ws)
                if not room:
                    self._rooms.pop(doc_id, None)

    async def broadcast(self, doc_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._rooms.get(doc_id, set()))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(doc_id, ws)


_hub: EventHub | None = None


def get_hub() -> EventHub:
    global _hub
    if _hub is None:
        _hub = EventHub()
    return _hub
