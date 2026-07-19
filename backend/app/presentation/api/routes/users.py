from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.auth.passwords import hash_password
from backend.app.infrastructure.database.models import Role, User
from backend.app.presentation.api.dependencies import get_session, require_roles
from backend.app.shared.validation import normalize_email_identifier, validate_password_strength

router = APIRouter(dependencies=[Depends(require_roles("admin"))])


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "user"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_identifier(value)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_password_strength(value)


@router.get("")
async def list_users(session: Annotated[AsyncSession, Depends(get_session)]) -> list[dict]:
    rows = (await session.execute(select(User, Role).join(Role, User.role_id == Role.id))).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": role.name,
            "is_active": user.is_active,
        }
        for user, role in rows
    ]


@router.post("")
async def create_user(payload: UserCreate, session: Annotated[AsyncSession, Depends(get_session)]) -> dict:
    role = await session.scalar(select(Role).where(Role.name == payload.role))
    if role is None:
        role = Role(name=payload.role, description=None)
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
    return {"id": user.id}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    user = await session.get(User, user_id)
    if user is None:
        return {"status": "not_found"}
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        role = await session.scalar(select(Role).where(Role.name == payload.role))
        if role is not None:
            user.role_id = role.id
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    await session.commit()
    return {"status": "ok"}


@router.delete("/{user_id}")
async def disable_user(user_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    user = await session.get(User, user_id)
    if user:
        user.is_active = False
        await session.commit()
    return {"status": "ok"}
