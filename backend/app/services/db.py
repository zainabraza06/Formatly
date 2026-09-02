"""One database, two engines.

SQLite is right for a laptop and for the tests: a file, no server, nothing to
install. It is wrong for a host that gives you no disk, which is most of the
free ones — the file goes away on every deploy, and with it every document,
every version and every account.

So the stores speak one dialect and this decides which engine hears it.
`DATABASE_URL` present means Postgres; absent means the file, exactly as
before. The SQL is written once, in the form both understand: `?` for
parameters, translated on the way to Postgres, and `ON CONFLICT` for an upsert,
which SQLite has had since 3.24 and Postgres has always had.

Nothing here is an abstraction over SQL. It is a connection, a placeholder, and
the handful of statements that differ.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

# Connections are made per call and closed after; a pool is what the Postgres
# driver already is. This only guards the file case, where two writers meet.
_FILE_LOCK = threading.Lock()

# Long enough to cover a commit writing half a megabyte of snapshot, short
# enough that a genuinely stuck writer is an error rather than a hang.
_BUSY_SECONDS = 10.0


def database_url() -> Optional[str]:
    """The Postgres to use, if one is configured."""
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return None
    # Render and Heroku both hand out `postgres://`, which psycopg does not
    # answer to and which is not worth a support question.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def is_postgres() -> bool:
    return database_url() is not None


def sql(statement: str) -> str:
    """A statement in the form the configured engine expects."""
    if not is_postgres():
        return statement
    # `?` becomes `%s`, except inside a quoted string where a question mark is
    # just a question mark. A literal per-cent sign would have to be doubled
    # for psycopg; no statement here has one, and this asserts that rather than
    # trying to guess which per-cents are which.
    assert "%" not in statement, "escape the per-cent sign for psycopg"
    return _PLACEHOLDER.sub("%s", statement)


_PLACEHOLDER = re.compile(r"\?(?=(?:[^']*'[^']*')*[^']*$)")


@contextmanager
def connect(path: Optional[Path] = None) -> Iterator[Any]:
    """A connection that commits on a clean exit and rolls back otherwise.

    `path` is the SQLite file to use when no Postgres is configured; it is
    ignored when one is.
    """
    url = database_url()
    if url:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(url, row_factory=dict_row) as conn:
            yield _Postgres(conn)
        return

    if path is None:
        raise ValueError("no DATABASE_URL and no file to fall back to")
    path.parent.mkdir(parents=True, exist_ok=True)
    with _FILE_LOCK:
        conn = sqlite3.connect(str(path), timeout=_BUSY_SECONDS)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # A reader does not wait for a writer under WAL, which is what a
        # document being opened while another is committed looks like.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(f"PRAGMA busy_timeout = {int(_BUSY_SECONDS * 1000)}")
        try:
            with conn:
                yield conn
        finally:
            conn.close()


class _Postgres:
    """A psycopg connection that answers to the calls the stores make.

    They were written against sqlite3, where the connection itself executes and
    rows behave like dictionaries. Both are true here as well, so the stores
    need to know nothing about which engine they have.
    """

    def __init__(self, conn: Any):
        self._conn = conn

    def execute(self, statement: str, params: tuple = ()) -> Any:
        cursor = self._conn.cursor()
        cursor.execute(sql(statement), params)
        return cursor

    def executemany(self, statement: str, rows: Any) -> Any:
        cursor = self._conn.cursor()
        cursor.executemany(sql(statement), rows)
        return cursor

    def commit(self) -> None:
        self._conn.commit()


# ── the places the two engines genuinely differ ─────────────────────────────

def json_column() -> str:
    """The type for a column holding JSON.

    Text in both. Postgres has jsonb and it is tempting, but nothing here
    queries inside the JSON — a snapshot is read whole and parsed — and text
    keeps one schema for both engines instead of two.
    """
    return "TEXT"


def now_default() -> str:
    return "CURRENT_TIMESTAMP"
