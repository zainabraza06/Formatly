"""WebSocket connection hub. Fans out execution events to every client watching
a document, so multiple viewers animate in sync."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any

from fastapi import WebSocket

# Enough recent events for a client that arrives a moment late to catch up.
# A document is read as soon as it is imported, and the editor's socket opens
# only once the page has loaded — without this, the first pages of the reading
# are announced to an empty room and the reader sees nothing until page three.
_REPLAY = 40

# How long a missed event is still worth hearing. Long enough to cover a page
# load, short enough that opening a document tomorrow does not replay yesterday.
_REPLAY_SECONDS = 120

# Documents to keep a buffer for. A buffer nobody ever collects is not free.
_ROOMS_BUFFERED = 50


class EventHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._recent: dict[str, deque[tuple[float, dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, doc_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(doc_id, set()).add(ws)
            cutoff = time.monotonic() - _REPLAY_SECONDS
            missed = [m for at, m in self._recent.get(doc_id, ()) if at >= cutoff]
        for message in missed:
            try:
                await ws.send_json({**message, "replayed": True})
            except Exception:
                return

    async def disconnect(self, doc_id: str, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(doc_id)
            if room:
                room.discard(ws)
                if not room:
                    self._rooms.pop(doc_id, None)
                    # The room is empty; what was said in it is no longer news.
                    self._recent.pop(doc_id, None)

    async def broadcast(self, doc_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            buffer = self._recent.get(doc_id)
            if buffer is None:
                if len(self._recent) >= _ROOMS_BUFFERED:
                    self._recent.pop(next(iter(self._recent)), None)   # oldest first
                buffer = self._recent.setdefault(doc_id, deque(maxlen=_REPLAY))
            buffer.append((time.monotonic(), message))
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
