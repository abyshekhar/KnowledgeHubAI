from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.database.models import Chunk, Document, Feedback, User


async def dashboard_metrics(session: AsyncSession) -> dict:
    return {
        "total_documents": await session.scalar(select(func.count(Document.id))),
        "total_chunks": await session.scalar(select(func.count(Chunk.id))),
        "total_users": await session.scalar(select(func.count(User.id))),
        "feedback_count": await session.scalar(select(func.count(Feedback.id))),
    }

