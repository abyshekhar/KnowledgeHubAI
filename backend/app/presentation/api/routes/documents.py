from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.documents.ingest_document import IngestDocumentUseCase
from backend.app.config.settings import Settings
from backend.app.infrastructure.database.models import Chunk, Document, User
from backend.app.presentation.api.dependencies import get_current_user, get_session, get_settings, require_roles

router = APIRouter()


class LinkCreateRequest(BaseModel):
    name: str
    url: HttpUrl
    category: str | None = None
    depth: int = 0
    max_pages: int = 10
    js_render: bool = False


class LinkUpdateRequest(BaseModel):
    name: str | None = None
    url: HttpUrl | None = None
    category: str | None = None
    depth: int | None = None
    max_pages: int | None = None
    js_render: bool | None = None



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
            "path": item.path,
            "document_type": item.document_type,
            "status": item.status,
            "category": item.category,
            "access_level": item.access_level,
            "created_at": item.created_at,
            "tags": item.tags,
        }
        for item in documents
    ]


@router.post("/link", dependencies=[Depends(require_roles("admin", "knowledge_manager"))])
async def add_link(
    request: LinkCreateRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    from backend.app.shared.validation import validate_url_security
    try:
        validate_url_security(str(request.url))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    import json
    metadata = {
        "depth": request.depth,
        "max_pages": request.max_pages,
        "js_render": request.js_render
    }

    document = Document(
        name=request.name,
        path=str(request.url),
        document_type="link",
        status="pending",
        uploaded_by_id=user.id,
        category=request.category,
        tags=json.dumps(metadata)
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    background_tasks.add_task(_index_document, document.id, settings)
    return {"id": document.id, "status": "queued"}


@router.put("/link/{document_id}", dependencies=[Depends(require_roles("admin", "knowledge_manager"))])
async def update_link(
    document_id: int,
    request: LinkUpdateRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    document = await session.get(Document, document_id)
    if not document or document.document_type != "link":
        raise HTTPException(status_code=404, detail="Link not found")

    url_changed = request.url is not None and str(request.url) != document.path
    name_changed = request.name is not None and request.name != document.name
    category_changed = request.category is not None and request.category != document.category

    if url_changed:
        from backend.app.shared.validation import validate_url_security
        try:
            validate_url_security(str(request.url))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Parse current metadata from tags
    import json
    try:
        meta = json.loads(document.tags)
    except Exception:
        meta = {}

    tags_changed = False
    if request.depth is not None and request.depth != meta.get("depth"):
        meta["depth"] = request.depth
        tags_changed = True
    if request.max_pages is not None and request.max_pages != meta.get("max_pages"):
        meta["max_pages"] = request.max_pages
        tags_changed = True
    if request.js_render is not None and request.js_render != meta.get("js_render"):
        meta["js_render"] = request.js_render
        tags_changed = True

    if tags_changed:
        document.tags = json.dumps(meta)

    # If key details changed, clear old indexed data so it is correctly re-indexed
    if url_changed or name_changed or category_changed or tags_changed:
        from backend.app.infrastructure.vectorstores.factory import create_vector_store
        vector_store = create_vector_store(settings.vector_store)
        vector_store.delete_document(document.name)
        await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        document.status = "pending"

    if request.name is not None:
        document.name = request.name
    if request.url is not None:
        document.path = str(request.url)
    if request.category is not None:
        document.category = request.category

    await session.commit()
    await session.refresh(document)

    if document.status == "pending":
        background_tasks.add_task(_index_document, document.id, settings)

    return {"id": document.id, "status": document.status}


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
            except Exception as e:
                document.status = f"failed: {str(e)}"
                await session.commit()

