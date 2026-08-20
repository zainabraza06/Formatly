"""Changing your own name and password."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


@pytest.fixture
def client_and_token(tmp_path, monkeypatch):
    import app.docos.auth.store as store_mod
    from app.docos.auth.store import UserStore
    store = UserStore(db_path=tmp_path / "users.db")
    monkeypatch.setattr(store_mod, "_store", store)

    c = TestClient(app)
    r = c.post("/auth/signup", json={"email": "a@b.com", "password": "originalpw",
                                     "name": "Original Name"})
    assert r.status_code == 200, r.text
    return c, r.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_name_can_be_changed(client_and_token):
    c, token = client_and_token
    r = c.patch("/auth/me", json={"name": "New Name"}, headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"
    assert c.get("/auth/me", headers=_auth(token)).json()["name"] == "New Name"


def test_an_empty_name_is_rejected(client_and_token):
    c, token = client_and_token
    assert c.patch("/auth/me", json={"name": ""}, headers=_auth(token)).status_code == 422


def test_password_change_needs_the_current_one(client_and_token):
    c, token = client_and_token
    r = c.post("/auth/password", headers=_auth(token),
               json={"current_password": "wrongpw", "new_password": "brandnewpw"})
    assert r.status_code == 400
    # the old password must still work
    assert c.post("/auth/login",
                  json={"email": "a@b.com", "password": "originalpw"}).status_code == 200


def test_password_change_takes_effect(client_and_token):
    c, token = client_and_token
    r = c.post("/auth/password", headers=_auth(token),
               json={"current_password": "originalpw", "new_password": "brandnewpw"})
    assert r.status_code == 200

    assert c.post("/auth/login",
                  json={"email": "a@b.com", "password": "originalpw"}).status_code == 401
    assert c.post("/auth/login",
                  json={"email": "a@b.com", "password": "brandnewpw"}).status_code == 200


def test_the_new_password_must_differ(client_and_token):
    c, token = client_and_token
    r = c.post("/auth/password", headers=_auth(token),
               json={"current_password": "originalpw", "new_password": "originalpw"})
    assert r.status_code == 400


def test_a_short_password_is_rejected(client_and_token):
    c, token = client_and_token
    r = c.post("/auth/password", headers=_auth(token),
               json={"current_password": "originalpw", "new_password": "abc"})
    assert r.status_code == 422


def test_these_endpoints_need_authentication(client_and_token):
    c, _ = client_and_token
    assert c.patch("/auth/me", json={"name": "X"}).status_code == 401
    assert c.post("/auth/password",
                  json={"current_password": "a", "new_password": "bbbbbb"}).status_code == 401
