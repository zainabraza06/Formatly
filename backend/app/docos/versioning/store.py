"""Persistence for documents and versions, on SQLite or Postgres.

Repository pattern: the VersionEngine talks only to this interface, never to a
database directly. Snapshots are stored on checkpoint versions (every N); other
versions store just the action batch that produced them.

The SQL is written once in the form both engines understand — see
`app.services.db`, which decides which one hears it. `user` is quoted
everywhere because Postgres reserves the word for the current user, and an
unquoted one is a syntax error rather than a column.
"""
from __future__ import annotations

import base64
import gzip
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.services import db
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


_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id              TEXT PRIMARY KEY,
        title           TEXT NOT NULL DEFAULT '',
        current_version TEXT,
        redo_version    TEXT,
        owner_id        TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS versions (
        id            TEXT PRIMARY KEY,
        document_id   TEXT NOT NULL REFERENCES documents(id),
        parent_id     TEXT,
        seq           INTEGER NOT NULL,
        timestamp     TEXT NOT NULL,
        "user"        TEXT NOT NULL DEFAULT 'user',
        label         TEXT NOT NULL DEFAULT '',
        actions_json  TEXT NOT NULL DEFAULT '{}',
        snapshot_json TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_versions_doc ON versions(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_versions_parent ON versions(parent_id)",
)


class VersionStore:
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
            # A database made before documents had an owner. Only the file can
            # be one: a Postgres is created by this schema and starts complete.
            if not db.is_postgres():
                cols = {r["name"] for r in
                        c.execute("PRAGMA table_info(documents)").fetchall()}
                if "owner_id" not in cols:
                    c.execute("ALTER TABLE documents ADD COLUMN owner_id TEXT")

    # ── documents ───────────────────────────────────────────────────────────
    def create_document(self, doc_id: str, title: str, created_at: str,
                        owner_id: Optional[str] = None) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT INTO documents(id, title, created_at, owner_id)
                   VALUES (?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                       title=excluded.title,
                       created_at=excluded.created_at,
                       owner_id=excluded.owner_id""",
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
            c.execute(f"UPDATE documents SET {', '.join(sets)} WHERE id=?", tuple(vals))

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

        Versions go first: they carry a foreign key onto `documents`, which
        would otherwise refuse the parent row. Both statements share one
        transaction, so a failure leaves neither half done.
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
                   (id, document_id, parent_id, seq, timestamp, "user", label,
                    actions_json, snapshot_json)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (row.id, row.document_id, row.parent_id, row.seq, row.timestamp, row.user,
                 row.label, json.dumps(row.actions), _pack(row.snapshot)),
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
    def _to_row(r: Any) -> VersionRow:
        return VersionRow(
            id=r["id"], document_id=r["document_id"], parent_id=r["parent_id"],
            seq=r["seq"], timestamp=r["timestamp"], user=r["user"], label=r["label"],
            actions=json.loads(r["actions_json"] or "{}"),
            snapshot=_unpack(r["snapshot_json"]),
        )


# A snapshot is the whole document as JSON, and the largest thing this stores:
# a forty-page paper is three hundred kilobytes of it, fetched over whatever
# network lies between the app and its database. Compressed it is nine times
# smaller, which two milliseconds of processor buys — worth it against a
# database in another country, and worth it against a file too.
#
# The marker says which it is, so a snapshot written before this still reads:
# no prefix means the plain JSON it has always been.
_PACKED = "gz:"


def _pack(snapshot: Optional[dict[str, Any]]) -> Optional[str]:
    if snapshot is None:
        return None
    raw = json.dumps(snapshot).encode("utf-8")
    return _PACKED + base64.b64encode(gzip.compress(raw, 6)).decode("ascii")


def _unpack(stored: Optional[str]) -> Optional[dict[str, Any]]:
    if not stored:
        return None
    if not stored.startswith(_PACKED):
        return json.loads(stored)
    raw = gzip.decompress(base64.b64decode(stored[len(_PACKED):]))
    return json.loads(raw.decode("utf-8"))
