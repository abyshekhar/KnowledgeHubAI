from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.database.models import Feedback, User
from backend.app.presentation.api.dependencies import get_current_user, get_session

router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: int | None = None
    question: str
    response: str
    rating: str


@router.post("")
async def create_feedback(
    payload: FeedbackRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    session.add(
        Feedback(
            message_id=payload.message_id,
            user_id=user.id,
            question=payload.question,
            response=payload.response,
            rating=payload.rating,
        )
    )
    await session.commit()
    return {"status": "ok"}

