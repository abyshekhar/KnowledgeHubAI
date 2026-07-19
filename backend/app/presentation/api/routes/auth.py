from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import Settings
from backend.app.infrastructure.auth.passwords import hash_password, verify_password
from backend.app.infrastructure.auth.tokens import create_token
from backend.app.infrastructure.database.models import Role, User
from backend.app.presentation.api.dependencies import get_session, get_settings, get_current_user
from backend.app.shared.validation import normalize_email_identifier, validate_password_strength

router = APIRouter()

# In-memory login throttle, keyed by normalized email. Single-process only
# (matches the existing engine-cache pattern in database/session.py) - good
# enough for this app's single-worker deployment, not a substitute for a
# shared store if this is ever run with multiple workers.
_LOGIN_ATTEMPT_WINDOW_SECONDS = 15 * 60
_LOGIN_MAX_ATTEMPTS = 5
_login_attempts: dict[str, list[float]] = {}


def _check_login_rate_limit(email: str) -> None:
    now = time.monotonic()
    attempts = [t for t in _login_attempts.get(email, []) if now - t < _LOGIN_ATTEMPT_WINDOW_SECONDS]
    _login_attempts[email] = attempts
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )


def _record_login_failure(email: str) -> None:
    _login_attempts.setdefault(email, []).append(time.monotonic())


def _clear_login_attempts(email: str) -> None:
    _login_attempts.pop(email, None)


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_identifier(value)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_identifier(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    role = await session.scalar(select(Role).where(Role.name == "user"))
    if role is None:
        role = Role(name="user", description="Default user")
        session.add(role)
        await session.flush()
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    return _tokens(user.email, settings)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    _check_login_rate_limit(payload.email)
    user = await session.scalar(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    if user is None or not verify_password(payload.password, user.password_hash):
        _record_login_failure(payload.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    _clear_login_attempts(payload.email)
    return _tokens(user.email, settings)


@router.post("/refresh", response_model=TokenResponse)
async def refresh() -> TokenResponse:
    raise HTTPException(status_code=501, detail="Refresh token rotation is reserved for the next milestone")


@router.post("/logout")
async def logout() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/me")
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.name if user.role else "user",
    }


@router.post("/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    user.password_hash = hash_password(payload.new_password)
    await session.commit()
    return {"status": "ok"}


def _tokens(email: str, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(email, settings.app.secret_key, settings.app.access_token_minutes, "access"),
        refresh_token=create_token(
            email,
            settings.app.secret_key,
            settings.app.refresh_token_days * 24 * 60,
            "refresh",
        ),
    )
