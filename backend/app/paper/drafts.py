"""Where a composed paper is kept between writing it and exporting it.

A draft used to be a `.spec.json` file beside the generated documents, which is
fine on a machine with a disk and wrong on a host without one: the file goes
away on every deploy, and the draft is the work — the .docx beside it can be
made again from the spec, but nothing can make the spec again.

So a draft is a row, in whichever database the rest of the app is using.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services import db
from app.services.storage import get_paths, new_id

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS paper_drafts (
        id         TEXT PRIMARY KEY,
        owner_id   TEXT NOT NULL,
        title      TEXT NOT NULL DEFAULT '',
        style      TEXT NOT NULL DEFAULT '',
        spec_json  TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_paper_drafts_owner ON paper_drafts(owner_id)",
)

# What the listing shows at once. A person scrolling their own drafts is not
# looking for the two hundredth.
_LIST_LIMIT = 20


class DraftStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._path = db_path or (get_paths().root / "docos.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _conn(self):
        return db.connect(self._path)

    def _init_schema(self) -> None:
        with self._lock, self._conn() as c:
            for statement in _SCHEMA:
                c.execute(statement)

    def save(self, spec: dict[str, Any], owner_id: str) -> str:
        """Keep a spec and answer with the id it was kept under."""
        meta = (spec or {}).get("meta") or {}
        draft_id = new_id("paper")
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT INTO paper_drafts(id, owner_id, title, style, spec_json, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (draft_id, owner_id,
                 str(meta.get("title") or "Untitled Document"),
                 str(meta.get("style") or "ieee"),
                 json.dumps(spec),
                 datetime.now(timezone.utc).isoformat()),
            )
        return draft_id

    def load(self, draft_id: str, owner_id: str) -> Optional[dict[str, Any]]:
        """The spec, if it belongs to this owner. None covers both "no such
        draft" and "not yours" — which of the two it is, is not their business."""
        with self._conn() as c:
            row = c.execute(
                "SELECT spec_json FROM paper_drafts WHERE id=? AND owner_id=?",
                (draft_id, owner_id),
            ).fetchone()
        return json.loads(row["spec_json"]) if row else None

    def list_for(self, owner_id: str) -> list[dict[str, Any]]:
        """The owner's drafts, newest first, without reading a single spec:
        the two things the list shows are kept beside it."""
        with self._conn() as c:
            rows = c.execute(
                """SELECT id, title, style, created_at FROM paper_drafts
                   WHERE owner_id=? ORDER BY created_at DESC""",
                (owner_id,),
            ).fetchall()
        return [{"document_id": r["id"], "title": r["title"],
                 "style_preset": r["style"], "created_at": r["created_at"]}
                for r in rows[:_LIST_LIMIT]]

    def delete(self, draft_id: str, owner_id: str) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute(
                "DELETE FROM paper_drafts WHERE id=? AND owner_id=?",
                (draft_id, owner_id))
            return cur.rowcount > 0


_store: Optional[DraftStore] = None


def get_drafts() -> DraftStore:
    global _store
    if _store is None:
        _store = DraftStore()
    return _store
