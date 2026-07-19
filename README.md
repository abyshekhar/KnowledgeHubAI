# KnowledgeHub AI

<p align="center">
  <img src="docs/assets/github_banner.png" alt="KnowledgeHub AI Banner" width="100%">
</p>

<p align="center">
  <a href="#key-highlights">Key Highlights</a> •
  <a href="#use-cases">Use Cases</a> •
  <a href="#architecture-overview">Architecture</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#configuration-settings">Configuration</a> •
  <a href="#verification--testing">Testing</a> •
  <a href="#roadmap-ideas">Roadmap</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Security-100%25%20Offline-green?style=for-the-badge&logo=shield&logoColor=white" alt="Security Offline">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React">
  <img src="https://img.shields.io/badge/Ollama-Local%20LLMs-black?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama">
  <img src="https://img.shields.io/badge/Search-FAISS%20%2B%20BM25-blue?style=for-the-badge" alt="Hybrid Search">
</p>

---

KnowledgeHub AI is a fully offline, self-hosted, enterprise-grade AI Knowledge Assistant designed to let organizations chat securely with internal document bases (PDF, DOCX, Markdown, TXT, CSV, and Web/Wiki links) using natural language.

Out of the box it doubles as an **HR & policy assistant** — HR admins upload policy, benefits, and onboarding documents, and employees ask questions in plain language and get grounded, cited answers instead of hunting through PDFs — and a **QA requirement-to-test-case generator** for engineering teams — upload a requirement document and have the assistant draft test scenarios and test cases against it, asking clarifying questions first if it doesn't yet have enough context about the rest of the application. See [Use Cases](#use-cases) below for both workflows.

---

## Key Highlights

- **100% Offline-Capable**: Fully runs on a single local machine or corporate server without sending data to external APIs (no OpenAI, no Azure, no third-party cloud dependency).
- **Web Links Integration**: Index external/internal web links (Confluence, SharePoint, Notion, custom HTML pages) directly into the knowledge base, with configurable crawl depth and page limits and optional JavaScript rendering (via Playwright) for dynamic sites. Add, update, and remove links via the admin panel. Includes built-in Server-Side Request Forgery (SSRF) protection that re-validates every redirect hop, not just the initial URL.
- **Clean Architecture & Enterprise Patterns**: Strongly separated into presentation, application, domain, infrastructure, and configuration layers.
- **Advanced Chunking Pipeline**: Supports recursive character chunking, structural section-aware chunking, and similarity-based semantic sentence chunking.
- **Hybrid Retrieval System**: Combines FAISS dense semantic search and BM25 sparse keyword-based search with linear score blending (`hybrid_alpha`) and CrossEncoder rerankers. Embedding models and the vector index are loaded once and reused across requests for low query latency.
- **Security & Access Control**: Features JWT session/refresh tokens with strict access/refresh scope enforcement, Role-Based Access Control (Admin, Knowledge Manager, and User), access level document filtering, password strength requirements, login rate limiting, and file extension + MIME type validation on uploads.
- **FastAPI + React/Vite Admin Console**: Modern responsive dashboard, document upload manager with live indexing status (including failure-detail badges), wiki link indexer, conversational chat assistant with hover-preview source citations and relevance scores, and user management UI.
- **Requirement-to-Test-Case Generator**: Upload a requirement document and the assistant analyzes it against the rest of the knowledge base, asks bounded rounds of clarifying questions when it lacks app context (with a manual "Generate now" override), then produces grounded test scenarios and test cases — positive, negative, edge, and security — editable inline and exportable to CSV.

### Why KnowledgeHub AI?

| Feature | KnowledgeHub AI | Traditional Cloud RAG |
| :--- | :--- | :--- |
| **Data Privacy** | 🔒 **100% Secure** (Runs completely local) | ⚠️ High Risk (Uploads documents to third parties) |
| **API Costs** | 💰 **Free** (Unlimited queries, zero token costs) | 💸 High (Pay-per-token API endpoints) |
| **Internet Dependency** | ✈️ **None** (Works offline / air-gapped) | 🌐 Mandatory (Breaks during network outages) |
| **Search Engine** | 🔎 **Hybrid** (FAISS Dense + BM25 Sparse + Reranker) | 📝 Single Vector (Often lacks keyword-based matching) |
| **Access Control** | 🔑 **Built-in RBAC** (JWT session with role filtering) | ⚠️ Manual (Requires building custom auth filters) |

---

## Use Cases

### HR & Company Policy Assistant

1. An HR admin (or Knowledge Manager) uploads policy, benefits, leave, and onboarding documents from the **Knowledge Base** page and tags each with a category (e.g. `HR`) and access level.
2. Employees open **Chat Assistant** and ask questions in plain language ("How many casual leave days do I get?", "What's the WFH policy?").
3. Answers are generated strictly from the uploaded policy text, with source citations and relevance scores — no hallucinated policy details — and are automatically filtered by the employee's role/access level, so restricted documents (e.g. leadership-only compensation bands) never surface to a general `user` account.

### Requirement-to-Test-Case Generator (QA / Engineering)

1. A developer, QA engineer, or product owner uploads a requirement document on the **Test Generator** page.
2. The assistant parses the requirement and cross-references it against related content already in the knowledge base (architecture docs, existing specs, glossaries) to judge whether it has enough context to write accurate tests.
3. If context is missing, it asks up to a configurable number of rounds of targeted clarifying questions (actors, edge cases, integrations, business rules) — or the user can click **Generate now** at any point to proceed with best-effort assumptions, which are then listed explicitly alongside the output.
4. The assistant produces structured test scenarios and test cases (positive, negative, edge, boundary, security) covering the requirement, editable inline in the browser and exportable as CSV for import into Jira, Zephyr, TestRail, Excel, or any other tracker.

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
- **Application**: RAG orchestration services, feedback processing, document ingestion use cases, and requirement-to-test-case generation use cases (gap analysis + test artifact generation).
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
   *Optional: to enable JavaScript-rendered web link crawling, also install the Playwright browser binary:*
   ```bash
   playwright install chromium
   ```
   *Links added without this step still index fine — crawling automatically falls back to plain HTTP fetching.*

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
  max_bm25_corpus: 5000  # cap on chunks loaded into memory per query for BM25
  reranker:
    enabled: false
    model: BAAI/bge-reranker-base

chunking:
  strategy: recursive  # Values: recursive, section, semantic
  chunk_size: 500
  chunk_overlap: 50

test_generation:
  max_clarifying_rounds: 2  # rounds of clarifying questions before generating with assumptions
  context_top_k: 6          # related knowledge base chunks pulled in as supplementary context
```

---

## Verification & Testing

Verify system correctness by executing the test suite (unit tests in `backend/tests/unit`, end-to-end RBAC/ingestion checks in `backend/tests/integration`):
```bash
PYTHONPATH=. .venv/bin/pytest
```

---

## Roadmap Ideas

With document ingestion, RBAC-aware chat, and requirement-to-test-case generation in place, the same patterns (upload → ground in the knowledge base → structured LLM output → editable UI → export) extend naturally to more of a software organization's day-to-day workflows. Ideas under consideration:

### For Developers & QA

- **PR/code review checklist generator**: given a diff or feature description, generate a review checklist grounded in the team's existing coding standards/architecture docs — the same gap-analysis + clarifying-question pattern used for test generation.
- **Incident & runbook assistant**: index postmortems and runbooks so on-call engineers can ask "how did we fix this last time?" and get cited answers instead of searching Slack history.
- **API/architecture doc chat**: point the assistant at OpenAPI specs and internal architecture docs for onboarding and API-usage Q&A.
- **Ticket export integration**: push generated test cases directly into Jira/Linear/Zephyr instead of (or alongside) CSV export.
- **Test case regression tracking**: version generated test suites across requirement edits and flag which test cases are now stale.

### For Managers & Leadership

- **Meeting notes → action items**: upload raw meeting notes/transcripts and extract structured decisions and action items, reusing the requirement-analysis pipeline.
- **Policy acknowledgment tracking**: require employees to confirm they've read a policy document, with a manager-facing completion dashboard (builds on the existing audit log and RBAC model).
- **Usage & topic analytics**: extend the existing analytics dashboard with per-team/per-category query trends, so managers can see what employees are struggling to find answers to.
- **Approval workflow for published documents**: a review/approve step before a document uploaded by a Knowledge Manager becomes visible knowledge-base-wide, useful for compliance-sensitive policy content.
- **Cross-team knowledge base isolation**: workspace/tenant-style separation so multiple teams or business units can share one deployment without seeing each other's documents.

---

## Deployment Guides

### macOS (launchd plist service)
Refer to launchd examples in `scripts/macos/com.knowledgehub.ai.plist` and run `scripts/macos/start.sh`.

### Linux (systemd service)
Copy the service configuration template `scripts/linux/knowledgehub-ai.service` into `/etc/systemd/system/` and reload daemon.

### Windows (PowerShell service)
Follow details inside `scripts/windows/install-service.md` and trigger `scripts/windows/start.ps1`.
