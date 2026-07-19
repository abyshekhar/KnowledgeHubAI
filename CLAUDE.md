# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

KnowledgeHub AI is a fully offline, self-hosted RAG (Retrieval-Augmented Generation) knowledge assistant. FastAPI backend + React/Vite frontend, backed by SQLite, FAISS (or Qdrant), and a local Ollama LLM. No external API calls — everything runs on local models (Ollama for generation, HuggingFace sentence-transformers for embeddings).

## Commands

### Backend setup & run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py        # initializes DB, creates roles + default admin (admin@knowledgehub.local / ChangeMe123!)
python run.py           # starts FastAPI at http://127.0.0.1:8000 (uvicorn, reload=True)
```

### Tests
```bash
PYTHONPATH=. .venv/bin/pytest                              # run full suite
pytest backend/tests/unit/test_chunking.py                 # single file
pytest backend/tests/unit/test_chunking.py::test_recursive_chunking_preserves_metadata  # single test
pytest --cov=backend/app --cov-report=term-missing         # with coverage (as CI does)
```
Test config lives in `pyproject.toml`: `testpaths = ["backend/tests"]`, `asyncio_mode = "auto"`, `pythonpath = ["backend"]`. Tests are split into `backend/tests/unit` and `backend/tests/integration`.

### Lint
```bash
ruff check .   # line-length 100, target py312 (config in pyproject.toml)
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # Vite dev server at http://127.0.0.1:5173
npm run build       # tsc && vite build
npm run test:e2e    # Playwright
```

### DB migrations (Alembic)
Config at repo root `alembic.ini`, scripts in `backend/alembic/`. Run alembic commands from repo root.

## Architecture

Strict Clean Architecture under `backend/app/`, layered as:

- **`domain/`** — entities (`Document`, `Chunk`, `User`) and provider/repository *ports* only (abstract interfaces), e.g. `domain/services/llm_provider.py`, `domain/services/vector_store.py`. No implementation details here.
- **`application/`** — use cases that orchestrate domain + infrastructure: `application/chat/rag_service.py` (`RAGService.answer`), `application/documents/ingest_document.py` (`IngestDocumentUseCase`), `application/analytics/metrics.py`, `application/feedback/`, `application/users/`.
- **`infrastructure/`** — concrete adapters: SQLAlchemy models/session (`infrastructure/database/`), FAISS/Qdrant vector stores (`infrastructure/vectorstores/`, selected via `infrastructure/vectorstores/factory.py`), Ollama/LLM providers (`infrastructure/ai/providers.py`), HF embedding providers (`infrastructure/embeddings/providers.py`), document parsing/chunking/cleaning (`infrastructure/documents/`), hybrid retrieval + reranking (`infrastructure/retrieval/`), JWT + password hashing (`infrastructure/auth/`), structlog setup (`infrastructure/logging/`).
- **`presentation/`** — FastAPI routers under `presentation/api/routes/` (`auth`, `users`, `documents`, `chat`, `categories`, `feedback`, `analytics`, `health`), plus DI dependencies (`presentation/api/dependencies.py`), notably `require_roles(...)` route guards.
- **`config/`** — Pydantic v2 `Settings` models (`config/settings.py`) loaded from `application.yml` at repo root via `load_settings()` (lru-cached). Every subsystem (llm, embeddings, vector_store, retrieval, chunking, security) is configured there — check `application.yml` before assuming a default.

App wiring/composition root is `backend/app/main.py`: registers CORS (only allows the Vite dev origins), mounts all routers, mounts `/metrics` (Prometheus), and on startup runs `init_database` + a background task that re-indexes any documents left in `pending`/`processing` status.

### RAG flow
Query → embed (HF embeddings) → `HybridRetriever` (FAISS dense + BM25 sparse, blended via `retrieval.hybrid_alpha`, filtered by role-based access level and optional category) → `CrossEncoderReranker` (optional, `retrieval.reranker.enabled`) → threshold filter (`retrieval.score_threshold`) → prompt assembly grounded strictly in retrieved context → local LLM generation (Ollama) with an extractive-snippet fallback if generation fails → grounding/prompt-injection guard on the answer before it's persisted and returned with cited sources.

### RBAC
Three roles: `admin`, `knowledge_manager`, `user`. JWT access/refresh tokens (`infrastructure/auth/tokens.py`). Routes are guarded with `Depends(require_roles("admin", "knowledge_manager"))`. Document/chunk retrieval is additionally filtered by an access-level hierarchy (see `RAGService.answer` in `application/chat/rag_service.py` for the `allowed_levels` mapping) — the frontend also reads `/me` to gate UI routes, but the real enforcement is server-side.

### Document ingestion
Upload → parse (`infrastructure/documents/parsers.py`, supports PDF/DOCX/TXT/MD/CSV) → clean (`infrastructure/documents/cleaning.py`) → chunk (`infrastructure/documents/chunking.py`, strategies: `recursive`, `section`, `semantic`, configured via `chunking.strategy`) → embed → store chunks in FAISS + SQLite. Documents carry a `status` (`pending`/`processing`/`indexed`/`failed`); on server startup a background task retries any left in `pending`/`processing`. Category is stamped into chunk metadata for hybrid filtering.

### Vector store / provider abstraction
Swappable via config, not code changes: `vector_store.provider: faiss|qdrant` in `application.yml` selects the implementation in `infrastructure/vectorstores/factory.py`. Same pattern applies to `llm.provider` and `embeddings.provider` — always add new providers behind the existing port interfaces in `domain/services/`.

## Frontend structure

`frontend/src/`: `pages/` (route-level views: `ChatAssistant`, `Dashboard`, `KnowledgeBase`, `Login`, `Settings`, `UserManagement`), `layouts/AppLayout.tsx`, `components/` (shared UI), `api/client.ts` (backend API calls), `styles/index.css` (Tailwind). React 19 + Vite 6 + TanStack Query + Tailwind; TypeScript build is `tsc && vite build` — type errors fail the build.

## CI (`.github/workflows/ci.yml`)

Three parallel jobs on every push/PR: `backend` (pytest with coverage), `frontend` (npm install + build), `security` (`pip-audit` against `requirements.txt`). Keep changes green against all three.

## Notes

- `application.yml` is the single source of runtime configuration (LLM model/provider, embedding model, retrieval thresholds, chunking strategy, allowed upload extensions/MIME types). Prefer changing behavior there over hardcoding.
- Default admin credentials (`admin@knowledgehub.local` / `ChangeMe123!`) are created by `setup.py` — expected only in dev/local setups.
- `docs/architecture/developer-guide.md` and `docs/architecture/database.md` have additional architecture detail if needed.
