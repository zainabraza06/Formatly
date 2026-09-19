"""A database that cannot be reached should say so, in a sentence.

A Supabase pooler that does not recognise the project answers with four
paragraphs about host addresses. That was escaping as a 500 carrying psycopg's
own text, so the browser showed "Internal Server Error" and nobody — user or
operator — could tell whether the server was broken, the network was down, or
the connection string was wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402
from app.services.db import (  # noqa: E402
    DatabaseUnavailable,
    _redacted,
    describe_connection_failure,
)

# The real thing, as the pooler sends it.
_TENANT = (
    'connection failed: connection to server at "35.79.125.133", port 6543 '
    "failed: FATAL:  (ENOTFOUND) tenant/user postgres.awhpvvfhwigonwwqujkr not found\n"
    "Multiple connection attempts failed. All failures were:\n"
    "- host: 'aws-0-ap-northeast-1.pooler.supabase.com', port: '6543'"
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.docos.auth.store as store_mod
    from app.docos.auth.store import UserStore

    monkeypatch.setenv("DOCPILOT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(store_mod, "_store", UserStore(db_path=tmp_path / "users.db"))

    c = TestClient(app)
    token = c.post("/auth/signup",
                   json={"email": "a@b.com", "password": "password1", "name": "U"}).json()["token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_a_missing_tenant_is_named_as_a_credentials_problem():
    failure = describe_connection_failure("postgresql://u:p@host/db", Exception(_TENANT))

    assert isinstance(failure, DatabaseUnavailable)
    assert "does not recognise that project or user" in failure.message
    # The cause is one line, not the whole wall of text.
    assert "\n" not in failure.cause
    assert "ENOTFOUND" in failure.cause


def test_a_bad_password_is_told_apart_from_a_bad_host():
    password = describe_connection_failure(
        "postgresql://u:p@host/db", Exception("FATAL: password authentication failed for user"))
    host = describe_connection_failure(
        "postgresql://u:p@host/db", Exception('could not translate host name "nope" to address'))

    assert "password" in password.message
    assert "host" in host.message
    assert password.message != host.message


def test_an_unrecognised_failure_still_gets_a_sentence():
    failure = describe_connection_failure("postgresql://u:p@host/db", Exception("boom"))

    assert "could not be reached" in failure.message
    assert failure.cause == "boom"


def test_the_password_never_reaches_a_log_line():
    assert _redacted("postgresql://postgres.abc:hunter2@pooler:6543/postgres") == (
        "postgresql://postgres.abc:***@pooler:6543/postgres"
    )


def test_the_api_answers_503_rather_than_500(client, monkeypatch):
    from app.paper.drafts import DraftStore

    def unreachable(self, owner_id):
        raise DatabaseUnavailable("The database could not be reached.", "ENOTFOUND tenant")

    monkeypatch.setattr(DraftStore, "list_for", unreachable)

    response = client.get("/paper/recent")

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "The database could not be reached."
    assert body["cause"] == "ENOTFOUND tenant"
    # The client is told this is worth trying again, unlike a 400.
    assert body["retryable"] is True


def test_health_reports_the_database_instead_of_failing(client):
    body = client.get("/health").json()

    assert body["status"] == "ok"
    # The suite runs on the file engine, which is always reachable.
    assert body["database"] == {"engine": "sqlite", "ok": True}
