from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.documents.ingest_document import IngestDocumentUseCase
from backend.app.config.settings import Settings
from backend.app.infrastructure.database.models import Chunk, Document, User
from backend.app.presentation.api.dependencies import get_current_user, get_session, get_settings, require_roles

router = APIRouter()


@router.post("/upload", dependencies=[Depends(require_roles("admin", "knowledge_manager"))])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
    category: str | None = None,
) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.security.allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file extension")
    upload_dir = Path(settings.app.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / Path(file.filename or "upload").name
    content = await file.read()
    max_bytes = settings.app.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    destination.write_bytes(content)
    document = Document(
        name=destination.name,
        path=str(destination),
        document_type=suffix.removeprefix("."),
        status="pending",
        uploaded_by_id=user.id,
        category=category,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    background_tasks.add_task(_index_document, document.id, settings)
    return {"id": document.id, "status": "queued"}


@router.get("")
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    del user
    documents = (await session.scalars(select(Document).order_by(Document.created_at.desc()))).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "document_type": item.document_type,
            "status": item.status,
            "category": item.category,
            "access_level": item.access_level,
            "created_at": item.created_at,
        }
        for item in documents
    ]


@router.delete("/{document_id}", dependencies=[Depends(require_roles("admin", "knowledge_manager"))])
async def delete_document(
    document_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    document = await session.get(Document, document_id)
    if document:
        from backend.app.infrastructure.vectorstores.factory import create_vector_store

        vector_store = create_vector_store(settings.vector_store)
        vector_store.delete_document(document.name)

        await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        await session.delete(document)
        await session.commit()
    return {"status": "ok"}


@router.post("/reindex", dependencies=[Depends(require_roles("admin", "knowledge_manager"))])
async def reindex_documents(
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    documents = (await session.scalars(select(Document))).all()
    for document in documents:
        document.status = "pending"
        background_tasks.add_task(_index_document, document.id, settings)
    await session.commit()
    return {"status": "queued"}


async def _index_document(document_id: int, settings: Settings) -> None:
    from backend.app.infrastructure.database.session import create_session_factory

    session_factory = create_session_factory(settings.database.url)
    async with session_factory() as session:
        document = await session.get(Document, document_id)
        if document:
            try:
                await IngestDocumentUseCase(settings, session).execute(document)
            except Exception:
                document.status = "failed"
                await session.commit()

