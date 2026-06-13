from __future__ import annotations

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from backend.app.infrastructure.auth.passwords import hash_password
from backend.app.infrastructure.database.models import User
from backend.app.presentation.api.routes.auth import change_password, PasswordChangeRequest
from backend.app.presentation.api.routes.users import update_user, UserUpdate


@pytest.mark.asyncio
async def test_change_password_success() -> None:
    session = AsyncMock()
    user = User(
        email="test@example.com",
        full_name="Test User",
        password_hash=hash_password("old-password"),
        is_active=True,
    )
    
    payload = PasswordChangeRequest(
        current_password="old-password",
        new_password="new-password",
    )
    
    res = await change_password(payload, user, session)
    assert res == {"status": "ok"}
    session.commit.assert_called_once()
    
    from backend.app.infrastructure.auth.passwords import verify_password
    assert verify_password("new-password", user.password_hash)


@pytest.mark.asyncio
async def test_change_password_incorrect_current() -> None:
    session = AsyncMock()
    user = User(
        email="test@example.com",
        full_name="Test User",
        password_hash=hash_password("old-password"),
        is_active=True,
    )
    
    payload = PasswordChangeRequest(
        current_password="wrong-password",
        new_password="new-password",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await change_password(payload, user, session)
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Current password is incorrect"
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_admin_reset_user_password() -> None:
    session = AsyncMock()
    user = User(
        email="user@example.com",
        full_name="Regular User",
        password_hash=hash_password("original-pass"),
        is_active=True,
    )
    
    session.get.return_value = user
    
    payload = UserUpdate(
        password="reset-pass"
    )
    
    res = await update_user(user_id=1, payload=payload, session=session)
    assert res == {"status": "ok"}
    session.commit.assert_called_once()
    
    from backend.app.infrastructure.auth.passwords import verify_password
    assert verify_password("reset-pass", user.password_hash)
