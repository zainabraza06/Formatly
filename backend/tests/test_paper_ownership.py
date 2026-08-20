"""A generated paper belongs to whoever generated it.

/paper/recent used to list every spec in the shared documents directory to
anyone who asked — other people's titles, and the ids that make their exports
reachable — and the export routes checked that you were logged in but never that
the document was yours.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

_SPEC = {
    "meta": {"title": "Private Notes", "style": "assignment"},
    "blocks": [{"type": "paragraph", "text": "Body."}],
    "references": [],
}


@pytest.fixture
def clients(tmp_path, monkeypatch):
    """Two signed-in users sharing one documents directory."""
    import app.docos.auth.store as store_mod
    from app.docos.auth.store import UserStore

    # Paths is frozen and built from the environment, so the data directory is
    # redirected the way the application itself would redirect it.
    monkeypatch.setenv("DOCPILOT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(store_mod, "_store", UserStore(db_path=tmp_path / "users.db"))

    def make(email: str) -> TestClient:
        c = TestClient(app)
        token = c.post("/auth/signup",
                       json={"email": email, "password": "password1", "name": "U"}).json()["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        return c

    return make("owner@x.com"), make("stranger@x.com")


def _own_a_paper(client: TestClient) -> str:
    """Save a spec the way /paper/generate does, without calling the model."""
    from app.paper.api import _save_spec
    me = client.get("/auth/me").json()
    return _save_spec(_SPEC, me["id"])


def test_recent_needs_authentication(clients):
    owner, _ = clients
    anonymous = TestClient(app)
    assert anonymous.get("/paper/recent").status_code == 401


def test_recent_lists_only_your_own(clients):
    owner, stranger = clients
    _own_a_paper(owner)

    mine = owner.get("/paper/recent")
    assert mine.status_code == 200
    assert [d["title"] for d in mine.json()] == ["Private Notes"]

    theirs = stranger.get("/paper/recent")
    assert theirs.status_code == 200
    assert theirs.json() == [], "another user's papers must not be listed"


def test_a_stranger_cannot_export_your_paper(clients):
    owner, stranger = clients
    doc_id = _own_a_paper(owner)

    assert owner.get(f"/paper/{doc_id}/export/docx").status_code == 200
    assert stranger.get(f"/paper/{doc_id}/export/docx").status_code == 404


def test_an_unknown_id_is_indistinguishable_from_someone_elses(clients):
    """Whether an id exists is itself worth not telling a stranger."""
    owner, stranger = clients
    doc_id = _own_a_paper(owner)

    theirs = stranger.get(f"/paper/{doc_id}/export/docx")
    missing = stranger.get("/paper/paper_doesnotexist/export/docx")
    assert theirs.status_code == missing.status_code == 404


def test_recent_reports_when_it_was_made(clients):
    owner, _ = clients
    _own_a_paper(owner)
    assert owner.get("/paper/recent").json()[0]["created_at"]
