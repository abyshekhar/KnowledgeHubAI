from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.infrastructure.database.models import Base


def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite"):
        return
    parsed = urlparse(url)
    if parsed.path and parsed.path != "/:memory:":
        Path(parsed.path.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(url: str) -> async_sessionmaker[AsyncSession]:
    _ensure_sqlite_parent(url)
    engine = create_async_engine(url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_database(url: str) -> None:
    _ensure_sqlite_parent(url)
    engine = create_async_engine(url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
