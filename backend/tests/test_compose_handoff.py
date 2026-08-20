"""Composing a document and carrying it into Document OS to edit by hand.

The Compose page renders its spec to a .docx and imports it, so the user does
not download a file only to upload it again. That is two endpoints agreeing on
one file, which is exactly the sort of seam that breaks quietly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

_SPEC = {
    "meta": {"title": "Handoff", "style": "assignment",
             "authors": [{"name": "zainab", "affiliation": "NUST"}]},
    "blocks": [
        {"type": "heading", "level": 1, "text": "Introduction"},
        {"type": "paragraph", "text": "Body text that must survive the handoff."},
    ],
    "references": [],
}

_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.docos.auth.store as store_mod
    from app.docos.auth.store import UserStore
    monkeypatch.setattr(store_mod, "_store", UserStore(db_path=tmp_path / "users.db"))

    c = TestClient(app)
    token = c.post("/auth/signup", json={"email": "h@b.com", "password": "password1",
                                         "name": "H"}).json()["token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_a_composed_document_can_be_opened_in_document_os(client):
    rendered = client.post("/paper/render", json=_SPEC)
    assert rendered.status_code == 200
    docx = rendered.content
    assert docx[:2] == b"PK", "the render must be a real .docx"

    imported = client.post("/docos/import",
                           files={"file": ("Handoff.docx", docx, _DOCX)})
    assert imported.status_code == 200, imported.text
    body = imported.json()
    document_id = body["document_id"]

    # the editor opens it by id, which is what the button navigates to
    reopened = client.get(f"/docos/{document_id}")
    assert reopened.status_code == 200
    graph = reopened.json()["graph"]

    text = _all_text(graph["root"])
    assert "Body text that must survive the handoff." in text
    assert "Introduction" in text


def test_the_handoff_keeps_the_document_title(client):
    docx = client.post("/paper/render", json=_SPEC).content
    imported = client.post("/docos/import",
                           files={"file": ("Handoff.docx", docx, _DOCX)})
    assert imported.json()["title"]


def _all_text(node) -> str:
    out = [node.get("content", "")]
    for child in node.get("children", []):
        out.append(_all_text(child))
    return "\n".join(out)
