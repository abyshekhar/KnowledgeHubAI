# KnowledgeHub AI

<p align="center">
  <img src="docs/assets/github_banner.png" alt="KnowledgeHub AI Banner" width="100%">
</p>

<p align="center">
  <a href="#key-highlights">Key Highlights</a> •
  <a href="#architecture-overview">Architecture</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#configuration-settings">Configuration</a> •
  <a href="#verification--testing">Testing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Security-100%25%20Offline-green?style=for-the-badge&logo=shield&logoColor=white" alt="Security Offline">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Ollama-Local%20LLMs-black?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama">
  <img src="https://img.shields.io/badge/Search-FAISS%20%2B%20BM25-blue?style=for-the-badge" alt="Hybrid Search">
</p>

---

KnowledgeHub AI is a fully offline, self-hosted, enterprise-grade AI Knowledge Assistant designed to let organizations chat securely with internal document bases (PDF, DOCX, Markdown, and TXT) using natural language.

---

## Key Highlights

- **100% Offline-Capable**: Fully runs on a single local machine or corporate server without sending data to external APIs (no OpenAI, no Azure, no third-party cloud dependency).
- **Clean Architecture & Enterprise Patterns**: Strongly separated into presentation, application, domain, infrastructure, and configuration layers.
- **Advanced Chunking Pipeline**: Supports recursive character chunking, structural section-aware chunking, and similarity-based semantic sentence chunking.
- **Hybrid Retrieval System**: Combines FAISS dense semantic search and BM25 sparse keyword-based search with linear score blending (`hybrid_alpha`) and CrossEncoder rerankers.
- **Security & Access Control**: Features JWT session/refresh tokens, Role-Based Access Control (Admin, Knowledge Manager, and User), and access level document filtering.
- **FastAPI + React/Vite Admin Console**: Modern responsive dashboard, document upload manager, conversational chat assistant, and user management UI.

### Why KnowledgeHub AI?

| Feature | KnowledgeHub AI | Traditional Cloud RAG |
| :--- | :--- | :--- |
| **Data Privacy** | 🔒 **100% Secure** (Runs completely local) | ⚠️ High Risk (Uploads documents to third parties) |
| **API Costs** | 💰 **Free** (Unlimited queries, zero token costs) | 💸 High (Pay-per-token API endpoints) |
| **Internet Dependency** | ✈️ **None** (Works offline / air-gapped) | 🌐 Mandatory (Breaks during network outages) |
| **Search Engine** | 🔎 **Hybrid** (FAISS Dense + BM25 Sparse + Reranker) | 📝 Single Vector (Often lacks keyword-based matching) |
| **Access Control** | 🔑 **Built-in RBAC** (JWT session with role filtering) | ⚠️ Manual (Requires building custom auth filters) |

---

## Architecture Overview

```text
                               ┌────────────────────────┐
                               │       React App        │
                               └───────────┬────────────┘
                                           │ API Requests
                                           ▼
                               ┌────────────────────────┐
                               │      FastAPI App       │
                               └───────────┬────────────┘
                                           │
      ┌──────────────────────┬─────────────┴─────────────┬──────────────────────┐
      ▼                      ▼                           ▼                      ▼
┌───────────┐          ┌───────────┐               ┌───────────┐          ┌───────────┐
│ Database  │          │ Vector    │               │ Local LLM │          │ Embeddings│
│ (SQLite)  │          │ (FAISS)   │               │ (Ollama)  │          │ (HF Trans)│
└───────────┘          └───────────┘               └───────────┘          └───────────┘
```

The system is organized into a five-tier architecture under the `backend/app` namespace:
- **Presentation**: FastAPI routes, routers, and token dependency injection resolvers.
- **Application**: RAG orchestration services, feedback processing, and document ingestion use cases.
- **Domain**: Domain models (DocumentChunk, User) and vector store/LLM service abstractions.
- **Infrastructure**: SQLAlchemy, FAISS vector indexing, Ollama providers, and sentence-transformers.
- **Config**: Settings validated using Pydantic v2 and loaded from `application.yml`.

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- [Ollama](https://ollama.com/) (configured and running locally)

### Quick Start Setup

1. **Clone and Enter Repository**:
   ```bash
   git clone <repository_url> knowledgehub-ai
   cd knowledgehub-ai
   ```

2. **Initialize Python Virtual Environment & Dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Initialize Database & Create Admin User**:
   ```bash
   python setup.py
   ```
   *Note: This creates the default administrator login:*
   - **Email**: `admin@knowledgehub.local`
   - **Password**: `ChangeMe123!`

4. **Launch Backend API Server**:
   ```bash
   python run.py
   ```
   *The backend starts at: `http://127.0.0.1:8000`*

5. **Start Frontend Dev Server**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   *The client console runs at: `http://127.0.0.1:5173`*

---

## Configuration Settings

The system settings are managed inside `application.yml`. Important configuration blocks include:

```yaml
llm:
  provider: ollama
  model: mistral
  base_url: http://127.0.0.1:11434
  temperature: 0.1

embeddings:
  provider: huggingface
  model: BAAI/bge-small-en-v1.5

retrieval:
  top_k: 5
  score_threshold: 0.7
  hybrid_alpha: 0.75
  reranker:
    enabled: false
    model: BAAI/bge-reranker-base

chunking:
  strategy: recursive  # Values: recursive, section, semantic
  chunk_size: 500
  chunk_overlap: 50
```

---

## Verification & Testing

Verify system correctness by executing the test suite:
```bash
PYTHONPATH=. .venv/bin/pytest
```

---

## Deployment Guides

### macOS (launchd plist service)
Refer to launchd examples in `scripts/macos/com.knowledgehub.ai.plist` and run `scripts/macos/start.sh`.

### Linux (systemd service)
Copy the service configuration template `scripts/linux/knowledgehub-ai.service` into `/etc/systemd/system/` and reload daemon.

### Windows (PowerShell service)
Follow details inside `scripts/windows/install-service.md` and trigger `scripts/windows/start.ps1`.
