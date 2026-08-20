"""Auth API: signup / login / me / profile, plus the current-user dependency."""
from __future__ import annotations

import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.docos.auth.security import create_token, decode_token, hash_password, verify_password
from app.docos.auth.store import User, get_user_store

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ChangePasswordRequest(BaseModel):
    # The current password is required even though the caller is authenticated:
    # a borrowed session should not be enough to lock the owner out.
    current_password: str
    new_password: str = Field(min_length=6)


def _issue(user: User) -> dict[str, Any]:
    token = create_token({"sub": user.id, "email": user.email})
    return {"token": token, "user": user.public()}


@router.post("/signup")
def signup(req: SignupRequest) -> dict[str, Any]:
    email = req.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="invalid email address")
    store = get_user_store()
    if store.get_by_email(email):
        raise HTTPException(status_code=409, detail="an account with this email already exists")
    user = store.create_user(email=email, name=req.name or email.split("@")[0],
                             password_hash=hash_password(req.password))
    return _issue(user)


@router.post("/login")
def login(req: LoginRequest) -> dict[str, Any]:
    store = get_user_store()
    user = store.get_by_email(req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    return _issue(user)


def user_from_token(token: Optional[str]) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return get_user_store().get_by_id(payload.get("sub", ""))


def get_current_user(authorization: Optional[str] = Header(default=None)) -> User:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user = user_from_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return user


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return user.public()


@router.patch("/me")
def update_profile(req: UpdateProfileRequest,
                   user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Change the display name. Email is the account's identity, so it stays."""
    updated = get_user_store().update_name(user.id, req.name)
    if updated is None:
        raise HTTPException(status_code=404, detail="account not found")
    return updated.public()


@router.post("/password")
def change_password(req: ChangePasswordRequest,
                    user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Change the password, proving ownership with the current one first."""
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="current password is incorrect")
    if req.new_password == req.current_password:
        raise HTTPException(status_code=400,
                            detail="the new password must differ from the current one")
    if get_user_store().update_password(user.id, hash_password(req.new_password)) is None:
        raise HTTPException(status_code=404, detail="account not found")
    return {"updated": True}
