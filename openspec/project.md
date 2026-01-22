# Project Context & Architecture Standards

## 1. Tech Stack (The "Iron Triangle")
- **Language**: Python 3.11
- **Package Manager**: **uv** (Strictly enforce `pyproject.toml` & `uv.lock`. NO `pip` or `poetry`).
  - Mirror: https://pypi.tuna.tsinghua.edu.cn/simple
- **Containerization**:
  - **Environment**: WSL2 + Docker Compose.
  - **Build Strategy**: Multi-stage Dockerfile (Builder layer with `uv sync` -> Runner layer with `python:3.11-slim`).
  - **Optimization**: Dependency layers must precede source code layers for caching.

## 2. Core Frameworks
- **Web Interface**: FastAPI (Async required).
- **Agent Orchestration**: LangChain (ReAct Pattern).
- **Async Task Queue**: **Celery** + **Redis** (Broker).
  - *Constraint*: All CV algorithms and LLM inference MUST run in Celery Workers, NEVER in the FastAPI main thread.
- **Databases**:
  - **Vector**: ChromaDB (Semantic Search for RAG).
  - **Relational**: PostgreSQL (SQLModel / SQLAlchemy Async).
  - **Object**: MinIO (For image persistence, passed by URL).

## 3. Architecture Rules (Non-Negotiable)
1.  **Interface First**: All inputs/outputs must be defined as **Pydantic v2 Models** before business logic is written.
2.  **Taxonomy Compliance**:
    - All pest/disease labels MUST align with `data/taxonomy_standard_v1.json`.
    - AI must handle label mapping (Model Output ID -> Standard Chinese Name) explicitly.
3.  **Error Handling**:
    - External calls (CV API, Search) must have **Timeouts** and **Retries**.
    - No raw 500 errors; catch exceptions and return structured JSON error responses.
4.  **Documentation**:
    - API endpoints must have docstrings compatible with OpenAPI/Swagger generation.

## 4. Directory Structure
```text
/app
  /api          # FastAPI Routes (Only simple dispatch logic)
  /core         # Config & Security
  /models       # Pydantic & SQLModel Schemas
  /services     # External Integrations (CV, Chroma, MinIO)
  /worker       # Celery Tasks (Heavy lifting logic)
/data           # Static JSONs (Taxonomy, etc.)
/openspec       # Spec Management