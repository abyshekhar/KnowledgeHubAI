from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    name: str = "KnowledgeHub AI"
    environment: str = "development"
    secret_key: str = "change-this-secret-before-production"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    upload_dir: str = "data/uploads"
    index_dir: str = "data/indexes"
    max_upload_mb: int = 50


class DatabaseSettings(BaseModel):
    provider: str = "sqlite"
    url: str = "sqlite+aiosqlite:///./data/knowledgehub.db"


class LLMSettings(BaseModel):
    provider: str = "ollama"
    model: str = "mistral"
    base_url: str = "http://127.0.0.1:11434"
    temperature: float = 0.1
    timeout_seconds: int = 120


class EmbeddingSettings(BaseModel):
    provider: str = "huggingface"
    model: str = "BAAI/bge-small-en-v1.5"
    batch_size: int = 32


class VectorStoreSettings(BaseModel):
    provider: str = "faiss"
    path: str = "data/indexes/faiss"


class RerankerSettings(BaseModel):
    enabled: bool = False
    model: str = "BAAI/bge-reranker-base"


class RetrievalSettings(BaseModel):
    top_k: int = 5
    score_threshold: float = 0.7
    hybrid_alpha: float = 0.75
    reranker: RerankerSettings = Field(default_factory=RerankerSettings)


class ChunkingSettings(BaseModel):
    strategy: str = "recursive"
    chunk_size: int = 500
    chunk_overlap: int = 50


class SecuritySettings(BaseModel):
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt", ".md", ".csv"]
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "text/csv",
    ]


class Settings(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)


@lru_cache
def load_settings() -> Settings:
    path = Path("application.yml")
    if not path.exists():
        return Settings()
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return Settings.model_validate(raw)

