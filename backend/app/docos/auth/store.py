"""User persistence (SQLite), sharing the DocOS database file."""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.services.storage import get_paths, new_id


@dataclass
class User:
    id: str
    email: str
    name: str
    password_hash: str
    created_at: str

    def public(self) -> dict[str, str]:
        return {"id": self.id, "email": self.email, "name": self.name,
                "created_at": self.created_at}


class UserStore:
    def __init__(self, db_path: Optional[Path] = None):
        self._path = db_path or (get_paths().root / "docos.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            TEXT PRIMARY KEY,
                    email         TEXT NOT NULL UNIQUE,
                    name          TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    created_at    TEXT NOT NULL
                );
                """
            )

    def create_user(self, email: str, name: str, password_hash: str) -> User:
        user = User(
            id=new_id("usr"), email=email.strip().lower(), name=name.strip(),
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO users(id, email, name, password_hash, created_at) VALUES (?,?,?,?,?)",
                (user.id, user.email, user.name, user.password_hash, user.created_at),
            )
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
            return self._to_user(row) if row else None

    def get_by_id(self, user_id: str) -> Optional[User]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return self._to_user(row) if row else None

    @staticmethod
    def _to_user(row: sqlite3.Row) -> User:
        return User(id=row["id"], email=row["email"], name=row["name"],
                    password_hash=row["password_hash"], created_at=row["created_at"])


_store: UserStore | None = None


def get_user_store() -> UserStore:
    global _store
    if _store is None:
        _store = UserStore()
    return _store
