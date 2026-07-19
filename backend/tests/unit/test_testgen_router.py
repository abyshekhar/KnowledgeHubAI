from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.infrastructure.database.models import Role, TestGenSession, User
from backend.app.presentation.api.routes.testgen import _load_owned_session


class _FakeSession:
    def __init__(self, obj):
        self._obj = obj

    async def get(self, model, id):  # noqa: A002 - matches AsyncSession.get signature
        return self._obj


def _user(role_name: str, user_id: int) -> User:
    user = User(id=user_id, email=f"{role_name}@test.local", full_name=role_name, password_hash="x", role_id=1)
    user.role = Role(name=role_name)
    return user


@pytest.mark.asyncio
async def test_owner_can_access_own_session():
    test_session = TestGenSession(id=1, requirement_document_id=1, user_id=42, status="completed")
    session = _FakeSession(test_session)

    result = await _load_owned_session(session, 1, _user("user", 42))
    assert result is test_session


@pytest.mark.asyncio
async def test_admin_can_access_any_session():
    test_session = TestGenSession(id=1, requirement_document_id=1, user_id=42, status="completed")
    session = _FakeSession(test_session)

    result = await _load_owned_session(session, 1, _user("admin", 99))
    assert result is test_session


@pytest.mark.asyncio
async def test_other_user_is_forbidden():
    test_session = TestGenSession(id=1, requirement_document_id=1, user_id=42, status="completed")
    session = _FakeSession(test_session)

    with pytest.raises(HTTPException) as exc_info:
        await _load_owned_session(session, 1, _user("user", 7))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_session_is_404():
    session = _FakeSession(None)

    with pytest.raises(HTTPException) as exc_info:
        await _load_owned_session(session, 999, _user("user", 1))
    assert exc_info.value.status_code == 404
