"""SQLite persistence for documents and versions.

Repository pattern: the VersionEngine talks only to this interface, never to
sqlite directly. Snapshots are stored on checkpoint versions (every N); other
versions store just the action batch that produced them.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.services.storage import get_paths


@dataclass
class VersionRow:
    id: str
    document_id: str
    parent_id: Optional[str]
    seq: int
    timestamp: str
    user: str
    label: str
    actions: dict[str, Any]
    snapshot: Optional[dict[str, Any]]

    @property
    def is_checkpoint(self) -> bool:
        return self.snapshot is not None


class VersionStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._path = db_path or (get_paths().root / "docos.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id              TEXT PRIMARY KEY,
                    title           TEXT NOT NULL DEFAULT '',
                    current_version TEXT,
                    redo_version    TEXT,
                    owner_id        TEXT,
                    created_at      TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS versions (
                    id           TEXT PRIMARY KEY,
                    document_id  TEXT NOT NULL REFERENCES documents(id),
                    parent_id    TEXT,
                    seq          INTEGER NOT NULL,
                    timestamp    TEXT NOT NULL,
                    user         TEXT NOT NULL DEFAULT 'user',
                    label        TEXT NOT NULL DEFAULT '',
                    actions_json TEXT NOT NULL DEFAULT '{}',
                    snapshot_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_versions_doc ON versions(document_id);
                CREATE INDEX IF NOT EXISTS idx_versions_parent ON versions(parent_id);
                """
            )
            # migration: add owner_id to pre-existing databases
            cols = {r["name"] for r in c.execute("PRAGMA table_info(documents)").fetchall()}
            if "owner_id" not in cols:
                c.execute("ALTER TABLE documents ADD COLUMN owner_id TEXT")

    # ── documents ───────────────────────────────────────────────────────────
    def create_document(self, doc_id: str, title: str, created_at: str,
                        owner_id: Optional[str] = None) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO documents(id, title, created_at, owner_id) VALUES (?,?,?,?)",
                (doc_id, title, created_at, owner_id),
            )

    def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            return dict(row) if row else None

    def set_pointers(self, doc_id: str, *, current: Optional[str] = ...,  # type: ignore[assignment]
                     redo: Optional[str] = ...) -> None:  # type: ignore[assignment]
        sets, vals = [], []
        if current is not ...:
            sets.append("current_version=?"); vals.append(current)
        if redo is not ...:
            sets.append("redo_version=?"); vals.append(redo)
        if not sets:
            return
        vals.append(doc_id)
        with self._lock, self._conn() as c:
            c.execute(f"UPDATE documents SET {', '.join(sets)} WHERE id=?", vals)

    def list_documents(self, owner_id: Optional[str] = None) -> list[dict[str, Any]]:
        with self._conn() as c:
            if owner_id is None:
                rows = c.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM documents WHERE owner_id=? ORDER BY created_at DESC",
                    (owner_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        """Remove a document and every version of it. True if one was there.

        Versions go first: they carry a foreign key onto `documents`, and
        `PRAGMA foreign_keys = ON` would refuse the parent row otherwise. Both
        statements share one transaction, so a failure leaves neither half done.
        """
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM versions WHERE document_id=?", (doc_id,))
            cur = c.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            return cur.rowcount > 0

    # ── versions ────────────────────────────────────────────────────────────
    def add_version(self, row: VersionRow) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT INTO versions
                   (id, document_id, parent_id, seq, timestamp, user, label, actions_json, snapshot_json)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (row.id, row.document_id, row.parent_id, row.seq, row.timestamp, row.user,
                 row.label, json.dumps(row.actions), json.dumps(row.snapshot) if row.snapshot else None),
            )

    def get_version(self, version_id: str) -> Optional[VersionRow]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM versions WHERE id=?", (version_id,)).fetchone()
            return self._to_row(row) if row else None

    def list_versions(self, doc_id: str) -> list[VersionRow]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM versions WHERE document_id=? ORDER BY seq ASC", (doc_id,)
            ).fetchall()
            return [self._to_row(r) for r in rows]

    def next_seq(self, doc_id: str) -> int:
        with self._conn() as c:
            row = c.execute(
                "SELECT MAX(seq) AS m FROM versions WHERE document_id=?", (doc_id,)
            ).fetchone()
            return 0 if row["m"] is None else int(row["m"]) + 1

    @staticmethod
    def _to_row(r: sqlite3.Row) -> VersionRow:
        return VersionRow(
            id=r["id"], document_id=r["document_id"], parent_id=r["parent_id"],
            seq=r["seq"], timestamp=r["timestamp"], user=r["user"], label=r["label"],
            actions=json.loads(r["actions_json"] or "{}"),
            snapshot=json.loads(r["snapshot_json"]) if r["snapshot_json"] else None,
        )
