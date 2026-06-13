from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from backend.app.config.settings import load_settings
from backend.app.infrastructure.database.session import init_database
from backend.app.infrastructure.logging.setup import configure_logging
from backend.app.presentation.api.routes import auth, chat, documents, feedback, health, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    configure_logging(settings.app.environment)
    await init_database(settings.database.url)
    yield


app = FastAPI(
    title="KnowledgeHub AI",
    description="Offline enterprise AI knowledge assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
app.mount("/metrics", make_asgi_app())

