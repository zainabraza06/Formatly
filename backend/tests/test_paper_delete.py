"""A generated paper can be deleted, by its owner and nobody else.

There was no way to delete one at all: the store had a `delete`, but no route
called it, so the library filled up with papers that could only be exported.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

_SPEC = {
    "meta": {"title": "Disposable", "style": "assignment"},
    "blocks": [{"type": "paragraph", "text": "Body."}],
    "references": [],
}


@pytest.fixture
def clients(tmp_path, monkeypatch):
    """Two signed-in users sharing one documents directory."""
    import app.docos.auth.store as store_mod
    from app.docos.auth.store import UserStore

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


def test_delete_removes_it_from_the_owners_list(clients):
    owner, _ = clients
    paper_id = _own_a_paper(owner)
    assert any(d["document_id"] == paper_id for d in owner.get("/paper/recent").json())

    assert owner.delete(f"/paper/{paper_id}").json() == {"deleted": True}

    assert not any(d["document_id"] == paper_id for d in owner.get("/paper/recent").json())


def test_deleting_it_twice_says_it_is_gone(clients):
    owner, _ = clients
    paper_id = _own_a_paper(owner)

    assert owner.delete(f"/paper/{paper_id}").status_code == 200
    assert owner.delete(f"/paper/{paper_id}").status_code == 404


def test_a_stranger_cannot_delete_it(clients):
    owner, stranger = clients
    paper_id = _own_a_paper(owner)

    # 404, not 403: a stranger is not told whether the id exists.
    assert stranger.delete(f"/paper/{paper_id}").status_code == 404
    # And it is still there for the person it belongs to.
    assert owner.get(f"/paper/{paper_id}/export/docx").status_code == 200


def test_delete_needs_authentication(clients):
    owner, _ = clients
    paper_id = _own_a_paper(owner)

    assert TestClient(app).delete(f"/paper/{paper_id}").status_code == 401


def test_a_deleted_paper_cannot_be_exported(clients):
    owner, _ = clients
    paper_id = _own_a_paper(owner)

    owner.delete(f"/paper/{paper_id}")

    assert owner.get(f"/paper/{paper_id}/export/docx").status_code == 404


def test_the_custom_style_route_still_has_its_own_delete(clients):
    """`/paper/styles/{id}` must not be swallowed by `/paper/{document_id}`."""
    owner, _ = clients

    # No such style, so the styles route answers — with its own message.
    response = owner.delete("/paper/styles/not-a-real-style")
    assert response.status_code == 404
    assert response.json()["detail"] == "custom style not found"
