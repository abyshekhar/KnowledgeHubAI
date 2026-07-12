from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.infrastructure.database.models import Base


from sqlalchemy import event, text

_engines = {}

def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite"):
        return
    parsed = urlparse(url)
    if parsed.path and parsed.path != "/:memory:":
        Path(parsed.path.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(url: str) -> async_sessionmaker[AsyncSession]:
    _ensure_sqlite_parent(url)
    if url not in _engines:
        connect_args = {}
        if url.startswith("sqlite"):
            # Set timeout to 30s to prevent operational errors during concurrent writes
            connect_args = {"timeout": 30.0}
        engine = create_async_engine(url, future=True, connect_args=connect_args)
        
        if url.startswith("sqlite"):
            # Set journal_mode to WAL and synchronous to NORMAL for high concurrency SQLite performance
            @event.listens_for(engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.close()
                
        _engines[url] = engine
        
    return async_sessionmaker(_engines[url], expire_on_commit=False)


async def init_database(url: str) -> None:
    _ensure_sqlite_parent(url)
    engine = create_async_engine(url, future=True)
    async with engine.begin() as conn:
        if url.startswith("sqlite"):
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed default roles and categories
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from backend.app.infrastructure.database.models import Role, Category
    
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Seed Roles
        roles_data = {
            "admin": "Full administrative access",
            "knowledge_manager": "Manage knowledge base content",
            "user": "Ask questions and view permitted sources",
        }
        for name, description in roles_data.items():
            existing = await session.scalar(select(Role).where(Role.name == name))
            if existing is None:
                session.add(Role(name=name, description=description))
        
        # Seed Categories
        categories_data = ["General", "HR", "Project-Specific", "Finance"]
        for name in categories_data:
            existing = await session.scalar(select(Category).where(Category.name == name))
            if existing is None:
                session.add(Category(name=name, description=f"Default {name} category"))
        
        await session.commit()

    await engine.dispose()
