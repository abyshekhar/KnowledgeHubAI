from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.chat.rag_service import RAGService
from backend.app.config.settings import Settings
from backend.app.infrastructure.database.models import Conversation, Message, User
from backend.app.presentation.api.dependencies import get_current_user, get_session, get_settings

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    category: str | None = None


@router.post("/query")
async def query(
    payload: ChatRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return await RAGService(settings, session).answer(
        payload.question, user, payload.conversation_id, payload.category
    )


@router.get("/history")
async def history(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    conversations = (
        await session.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.created_at.desc()))
    ).all()
    response: list[dict] = []
    updated_any = False
    for conversation in conversations:
        messages = (
            await session.scalars(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at))
        ).all()
        
        # Migrating legacy conversation titles
        if conversation.title in ("KnowledgeHub chat", "KnowledgeHub Chat", "New conversation", None):
            first_user_msg = next((m for m in messages if m.role == "user"), None)
            if first_user_msg:
                title = first_user_msg.content.strip()
                if len(title) > 35:
                    title = title[:35] + "..."
                if not title:
                    title = "New conversation"
                conversation.title = title
                session.add(conversation)
                updated_any = True
                
        response.append(
            {
                "id": conversation.id,
                "title": conversation.title,
                "messages": [
                    {
                        "role": message.role,
                        "content": message.content,
                        "sources": json.loads(message.sources_json),
                    }
                    for message in messages
                ],
            }
        )
    if updated_any:
        await session.commit()
    return response


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    conversation = await session.get(Conversation, conversation_id)
    if conversation:
        if conversation.user_id != user.id and (not user.role or user.role.name != "admin"):
            raise HTTPException(status_code=403, detail="Not authorized to delete this conversation")
        
        await session.execute(delete(Message).where(Message.conversation_id == conversation_id))
        await session.delete(conversation)
        await session.commit()
    return {"status": "ok"}

