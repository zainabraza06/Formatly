"""Password hashing (PBKDF2) and signed tokens (HS256), stdlib-only.

No third-party crypto dependency: password hashing uses hashlib.pbkdf2_hmac and
tokens are hand-rolled JWTs (HS256) signed with an app secret. The secret comes
from DOCOS_SECRET, or is generated once and persisted so tokens survive restarts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Optional

from app.services.storage import get_paths

_ITERATIONS = 120_000
_TOKEN_TTL = 7 * 24 * 3600  # 7 days


# ── secret ──────────────────────────────────────────────────────────────────

def _secret() -> str:
    env = os.environ.get("DOCOS_SECRET")
    if env:
        return env
    path = get_paths().root / "secret.key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    generated = base64.urlsafe_b64encode(os.urandom(32)).decode()
    path.write_text(generated, encoding="utf-8")
    return generated


# ── passwords ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt_b64, hash_b64 = stored.split("$")
        salt = _unb64(salt_b64)
        expected = _unb64(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# ── tokens ──────────────────────────────────────────────────────────────────

def create_token(payload: dict[str, Any], ttl: int = _TOKEN_TTL) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl
    seg = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(body).encode())}"
    sig = hmac.new(_secret().encode(), seg.encode(), hashlib.sha256).digest()
    return f"{seg}.{_b64url(sig)}"


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        seg, sig_b64 = token.rsplit(".", 1)
        expected = hmac.new(_secret().encode(), seg.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64url(sig_b64), expected):
            return None
        _header_b64, body_b64 = seg.split(".")
        body = json.loads(_unb64url(body_b64))
        if int(body.get("exp", 0)) < int(time.time()):
            return None
        return body
    except Exception:
        return None


# ── base64 helpers ──────────────────────────────────────────────────────────

def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _unb64(s: str) -> bytes:
    return base64.b64decode(s)


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64url(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
