"""Persistence for user-defined stylesheets.

Because a StyleSheet is plain serialisable data, a user can author one (or derive
it from a reference DOCX) and store it — no code change, no redeploy. Custom
styles are owned by a user and resolve exactly like built-in ones.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.paper.styles.base import StyleSheet
from app.services import db
from app.services.storage import get_paths, new_id


class StyleStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._path = db_path or (get_paths().root / "docos.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _conn(self):
        return db.connect(self._path)

    def _init_schema(self) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_styles (
                    id         TEXT PRIMARY KEY,
                    owner_id   TEXT NOT NULL,
                    name       TEXT NOT NULL,
                    sheet_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_paper_styles_owner ON paper_styles(owner_id)"
            )

    def save(self, owner_id: str, sheet: StyleSheet) -> StyleSheet:
        """Insert or update. A sheet keeps its id when re-saved."""
        stored = sheet.model_copy(deep=True)
        if not stored.id or stored.builtin:
            stored.id = new_id("style")
        stored.builtin = False

        with self._lock, self._conn() as c:
            c.execute(
                """INSERT INTO paper_styles(id, owner_id, name, sheet_json, created_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, sheet_json=excluded.sheet_json""",
                (stored.id, owner_id, stored.name,
                 json.dumps(stored.model_dump(mode="json")),
                 datetime.now(timezone.utc).isoformat()),
            )
        return stored

    def get(self, style_id: str, owner_id: Optional[str] = None) -> Optional[StyleSheet]:
        with self._conn() as c:
            if owner_id:
                row = c.execute(
                    "SELECT sheet_json FROM paper_styles WHERE id=? AND owner_id=?",
                    (style_id, owner_id),
                ).fetchone()
            else:
                row = c.execute(
                    "SELECT sheet_json FROM paper_styles WHERE id=?", (style_id,)
                ).fetchone()
        return StyleSheet.model_validate(json.loads(row["sheet_json"])) if row else None

    def get_by_name(self, name: str, owner_id: str) -> Optional[StyleSheet]:
        with self._conn() as c:
            row = c.execute(
                "SELECT sheet_json FROM paper_styles WHERE lower(name)=? AND owner_id=?",
                (name.strip().lower(), owner_id),
            ).fetchone()
        return StyleSheet.model_validate(json.loads(row["sheet_json"])) if row else None

    def list(self, owner_id: str) -> list[StyleSheet]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT sheet_json FROM paper_styles WHERE owner_id=? ORDER BY created_at DESC",
                (owner_id,),
            ).fetchall()
        return [StyleSheet.model_validate(json.loads(r["sheet_json"])) for r in rows]

    def delete(self, style_id: str, owner_id: str) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute(
                "DELETE FROM paper_styles WHERE id=? AND owner_id=?", (style_id, owner_id)
            )
            return cur.rowcount > 0


_store: StyleStore | None = None


def get_style_store() -> StyleStore:
    global _store
    if _store is None:
        _store = StyleStore()
    return _store
