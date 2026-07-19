from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.application.chat.rag_service import RAGService
from backend.app.application.documents.ingest_document import IngestDocumentUseCase
from backend.app.config.settings import Settings
from backend.app.infrastructure.auth.passwords import hash_password
from backend.app.infrastructure.database.models import Document, Role, User
from backend.app.infrastructure.database.session import create_session_factory, init_database


def _test_settings(tmp_path) -> Settings:
    settings = Settings()
    settings.database.url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    settings.app.upload_dir = str(tmp_path / "uploads")
    settings.app.index_dir = str(tmp_path / "indexes")
    settings.vector_store.path = str(tmp_path / "indexes" / "faiss")
    # Deterministic embeddings avoid downloading a real sentence-transformers
    # model in tests; llm.provider is left as "ollama" with nothing listening
    # on it, so RAGService falls back to its extractive answer path.
    settings.embeddings.provider = "deterministic"
    settings.retrieval.score_threshold = 0.0
    settings.retrieval.reranker.enabled = False
    return settings


async def _load_user(session, email: str) -> User:
    return await session.scalar(
        select(User).options(selectinload(User.role)).where(User.email == email)
    )


@pytest.mark.asyncio
async def test_rag_answer_only_surfaces_documents_within_users_access_level(tmp_path) -> None:
    settings = _test_settings(tmp_path)
    await init_database(settings.database.url)

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    admin_file = upload_dir / "admin_only.txt"
    admin_file.write_text("The launch codes are stored in the vault under sector nine.")
    general_file = upload_dir / "general.txt"
    general_file.write_text("The office is open from nine to five on weekdays.")

    session_factory = create_session_factory(settings.database.url)

    async with session_factory() as session:
        admin_role = await session.scalar(select(Role).where(Role.name == "admin"))
        user_role = await session.scalar(select(Role).where(Role.name == "user"))

        admin_user = User(
            email="admin@test.local",
            full_name="Admin",
            password_hash=hash_password("password123"),
            role_id=admin_role.id,
            is_active=True,
        )
        plain_user = User(
            email="user@test.local",
            full_name="User",
            password_hash=hash_password("password123"),
            role_id=user_role.id,
            is_active=True,
        )
        session.add_all([admin_user, plain_user])
        await session.flush()

        admin_doc = Document(
            name="admin_only.txt",
            path=str(admin_file),
            document_type="txt",
            status="pending",
            access_level="admin",
            uploaded_by_id=admin_user.id,
        )
        general_doc = Document(
            name="general.txt",
            path=str(general_file),
            document_type="txt",
            status="pending",
            access_level="user",
            uploaded_by_id=admin_user.id,
        )
        session.add_all([admin_doc, general_doc])
        await session.commit()

        # IngestDocumentUseCase commits internally once indexing succeeds.
        await IngestDocumentUseCase(settings, session).execute(admin_doc)
        await IngestDocumentUseCase(settings, session).execute(general_doc)

        assert admin_doc.status == "indexed"
        assert general_doc.status == "indexed"

    question = "Where are the launch codes stored?"

    async with session_factory() as session:
        plain_user = await _load_user(session, "user@test.local")
        result = await RAGService(settings, session).answer(question, plain_user)

    plain_user_sources = {source["document_name"] for source in result["sources"]}
    assert "admin_only.txt" not in plain_user_sources, (
        "a 'user'-role account must never see chunks from an 'admin'-access document"
    )

    async with session_factory() as session:
        admin_user = await _load_user(session, "admin@test.local")
        result = await RAGService(settings, session).answer(question, admin_user)

    admin_sources = {source["document_name"] for source in result["sources"]}
    assert "admin_only.txt" in admin_sources, (
        "an 'admin'-role account should retrieve documents restricted to admin access"
    )
