# KnowledgeHub AI

Fully offline, self-hosted AI knowledge assistant for private organizational knowledge bases.

KnowledgeHub AI is designed for single-machine enterprise deployment with open-source components only. It uses FastAPI, SQLite, FAISS-compatible vector storage, configurable local LLM providers, and a React/Vite admin UI.

## Highlights

- Offline-first RAG architecture with no paid API dependency
- Clean Architecture backend split into presentation, application, domain, infrastructure, shared, and config layers
- Configurable Ollama or Transformers LLM providers
- Configurable FAISS or Qdrant vector store abstraction, with FAISS as the default
- JWT auth, refresh tokens, role-based access control, audit-friendly data model
- Document ingestion for PDF, DOCX, Markdown, and TXT
- Source-cited grounded answers with low-confidence fallback
- SQLite by default, PostgreSQL-ready database configuration
- No Docker, Redis, Celery, cloud, OpenAI, or Azure OpenAI requirement

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py
python run.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default API: `http://127.0.0.1:8000`

Default UI: `http://127.0.0.1:5173`

## Default Login

`python setup.py` creates an admin user:

- Email: `admin@knowledgehub.local`
- Password: `ChangeMe123!`

Change this before production use.

## Project Layout

```text
backend/
  app/
    presentation/      FastAPI routes and dependencies
    application/       Use cases and orchestration
    domain/            Entities, repository ports, service ports
    infrastructure/    SQLAlchemy, auth, local AI providers, vector stores
    shared/            Errors, pagination, utilities
    config/            YAML and environment-backed settings
frontend/              React + TypeScript + Vite + TailwindCSS UI
docs/                  Architecture, user, and deployment guides
scripts/               Platform startup and service helpers
```

## Portfolio Scope

This repository is a production-shaped starter implementation. Local model quality and speed depend on the models installed on the target machine. The default configuration is conservative and runs with SQLite plus local files.

