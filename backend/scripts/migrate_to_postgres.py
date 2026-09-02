"""Copy a SQLite store into Postgres, so a deployment starts with your work in it.

    DATABASE_URL=postgresql://… python scripts/migrate_to_postgres.py [--db PATH]
    DATABASE_URL=postgresql://… python scripts/migrate_to_postgres.py --dry-run

Reads the file the app has been using and writes every row into the database
`DATABASE_URL` names. The tables are created if they are not there, so this
works against an empty Postgres.

Safe to run twice: a row whose id is already there is left alone rather than
duplicated or overwritten. Nothing is deleted from either side, so a run that
goes wrong costs you the time and not the documents.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import db  # noqa: E402
from app.services.storage import get_paths  # noqa: E402

# Every table, and the columns to carry. Named rather than SELECT *, so a
# column added on one side does not silently misalign the other.
TABLES = {
    "users": ("id", "email", "name", "password_hash", "created_at"),
    "documents": ("id", "title", "current_version", "redo_version", "owner_id",
                  "created_at"),
    "versions": ("id", "document_id", "parent_id", "seq", "timestamp", "user",
                 "label", "actions_json", "snapshot_json"),
    "paper_styles": ("id", "owner_id", "name", "sheet_json", "created_at"),
    "paper_drafts": ("id", "owner_id", "title", "style", "spec_json", "created_at"),
}

# `user` is a reserved word in Postgres and has to be quoted; the others do not
# and are left alone for readability.
def _column(name: str) -> str:
    return '"user"' if name == "user" else name


def _sqlite_rows(path: Path, table: str, columns: tuple[str, ...]) -> list[tuple]:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return []
    if not have:
        return []                      # a table this store never created
    conn.close()

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    picked = [c for c in columns if c in have]
    rows = conn.execute(f"SELECT {', '.join(picked)} FROM {table}").fetchall()
    conn.close()
    return [tuple(r[c] for c in picked) for r in rows], picked  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=None,
                        help="the SQLite file (default: the app's own)")
    parser.add_argument("--dry-run", action="store_true",
                        help="say what would be copied, write nothing")
    args = parser.parse_args()

    if not db.is_postgres():
        print("DATABASE_URL is not set — there is nowhere to copy to.")
        return 1

    source = args.db or (get_paths().root / "docos.db")
    if not source.exists():
        print(f"no SQLite store at {source}")
        return 1

    print(f"from  {source}")
    print(f"to    {db.database_url().split('@')[-1]}")   # never print the password
    print()

    # The tables have to exist before rows can go into them. Constructing the
    # stores is what creates them, and is idempotent.
    if not args.dry_run:
        from app.docos.auth.store import UserStore
        from app.docos.versioning.store import VersionStore
        from app.paper.drafts import DraftStore
        from app.paper.styles.store import StyleStore

        for store in (VersionStore, UserStore, StyleStore, DraftStore):
            try:
                store()
            except Exception as exc:                     # noqa: BLE001
                print(f"  could not prepare {store.__name__}: {exc}")

    total = 0
    for table, columns in TABLES.items():
        result = _sqlite_rows(source, table, columns)
        if not result:
            print(f"  {table:<14} nothing to copy")
            continue
        rows, picked = result
        if not rows:
            print(f"  {table:<14} empty")
            continue

        if args.dry_run:
            print(f"  {table:<14} {len(rows)} rows would be copied")
            total += len(rows)
            continue

        placeholders = ",".join("?" for _ in picked)
        names = ", ".join(_column(c) for c in picked)
        written = 0
        with db.connect() as conn:
            for row in rows:
                try:
                    conn.execute(
                        f"INSERT INTO {table}({names}) VALUES ({placeholders}) "
                        f"ON CONFLICT(id) DO NOTHING", row)
                    written += 1
                except Exception as exc:                 # noqa: BLE001
                    print(f"  {table}: a row would not go in — {exc}")
        print(f"  {table:<14} {written} rows copied")
        total += written

    print()
    print(f"{'would copy' if args.dry_run else 'copied'} {total} rows")
    if not args.dry_run:
        print("The SQLite file is untouched; keep it until you have checked the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
