from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.analytics.metrics import dashboard_metrics
from backend.app.presentation.api.dependencies import get_current_user, get_session
from backend.app.infrastructure.database.models import User

router = APIRouter(tags=["analytics"])


@router.get("/analytics/dashboard")
async def get_dashboard_metrics(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    del user  # Authenticated access check
    return await dashboard_metrics(session)
