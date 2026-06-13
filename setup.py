from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import select

from backend.app.config.settings import load_settings
from backend.app.infrastructure.auth.passwords import hash_password
from backend.app.infrastructure.database.models import Role, User
from backend.app.infrastructure.database.session import create_session_factory, init_database


async def main() -> None:
    settings = load_settings()
    Path(settings.app.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.app.index_dir).mkdir(parents=True, exist_ok=True)
    await init_database(settings.database.url)

    session_factory = create_session_factory(settings.database.url)
    async with session_factory() as session:
        roles = {}
        for name, description in {
            "admin": "Full administrative access",
            "knowledge_manager": "Manage knowledge base content",
            "user": "Ask questions and view permitted sources",
        }.items():
            role = await session.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=description)
                session.add(role)
                await session.flush()
            roles[name] = role

        admin = await session.scalar(select(User).where(User.email == "admin@knowledgehub.local"))
        if admin is None:
            admin = User(
                email="admin@knowledgehub.local",
                full_name="KnowledgeHub Admin",
                password_hash=hash_password("ChangeMe123!"),
                role_id=roles["admin"].id,
                is_active=True,
            )
            session.add(admin)
        await session.commit()

    print("KnowledgeHub AI initialized.")
    print("Admin: admin@knowledgehub.local / ChangeMe123!")


if __name__ == "__main__":
    asyncio.run(main())
