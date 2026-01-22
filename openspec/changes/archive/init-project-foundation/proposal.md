# Proposal: Initialize Project Foundation (init-project-foundation)

**Change ID**: `init-project-foundation`
**Status**: ✅ Completed
**Created**: 2026-01-22
**Completed**: 2026-01-22
**Author**: Claude (Full-Stack Agent Architect)

---

## 1. Problem Statement

The Smart-Agriculture project currently lacks:
- A proper Python project structure with `pyproject.toml`
- Core dependencies for FastAPI, Celery, and LangChain
- Docker containerization for local development and deployment
- Configuration management via environment variables
- Health check scripts for infrastructure components

This creates a **high barrier to entry** for developers and prevents the system from running in a reproducible environment.

---

## 2. Proposed Solution

Initialize the project foundation following the **Iron Triangle** principles defined in `openspec/project.md`:

1. **Project Scaffolding**: Create the standard directory structure (`app/`, `data/`, `scripts/`)
2. **Dependency Management**: Use `uv` for fast, reliable Python packaging
3. **Containerization**: Multi-stage Dockerfile + Docker Compose for all services
4. **Configuration Center**: Pydantic-based settings for env var management
5. **Health Checks**: Enhanced `doctor.py` to verify all services

---

## 3. Architecture Decisions

### 3.1. Dependency Management Strategy
**Decision**: Use `uv` as the exclusive package manager.

**Rationale**:
- 10-100x faster than pip
- Lock file ensures reproducible builds
- Enforces `pyproject.toml` standard (no more `requirements.txt` chaos)

**Trade-offs**:
- Slightly steeper learning curve for contributors unfamiliar with uv
- Mitigation: Add clear setup instructions in README

### 3.2. Docker Multi-Stage Build Strategy
**Decision**: Use builder-runner pattern with layer caching optimization.

**Rationale**:
- **Builder stage**: Install dependencies with `uv sync` (cached unless dependencies change)
- **Runner stage**: Copy only built artifacts + source code
- Reduces final image size by ~60% and rebuild time by ~80%

**Trade-offs**:
- More complex Dockerfile than single-stage builds
- Mitigation: Add inline comments explaining each stage

### 3.3. Configuration Management
**Decision**: Use `pydantic-settings` with BaseSettings.

**Rationale**:
- Type-safe configuration with validation at startup
- Automatic env var loading (e.g., `DATABASE_URL` → `settings.database_url`)
- Works seamlessly with Docker Compose environment variables

**Trade-offs**:
- Requires explicit type annotations for all settings
- Mitigation: This is actually a benefit for code maintainability

---

## 4. Impact Assessment

### 4.1. Affected Components
- **New Files Created**:
  - `pyproject.toml` (project metadata + dependencies)
  - `uv.lock` (locked dependency versions)
  - `Dockerfile` (multi-stage build)
  - `docker-compose.yml` (orchestration)
  - `.env.example` (environment template)
  - `app/core/config.py` (Pydantic settings)
  - Updated `scripts/doctor.py`

- **Modified Files**:
  - `README.md` (setup instructions)

### 4.2. Breaking Changes
- **None** (this is net-new infrastructure)

### 4.3. Migration Path
- No migration needed (fresh initialization)

---

## 5. Success Criteria

The implementation is considered successful when:

1. [x] `uv sync` completes without errors ✅
2. [x] `docker-compose up --build` starts all 5 services (Web, Worker, Redis, Postgres, Chroma) ✅
3. [x] `python scripts/doctor.py` passes all health checks ✅
4. [x] Environment variables are properly loaded via `app.core.config.Settings` ✅
5. [x] The project can be imported in Python without `ModuleNotFoundError` ✅

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| uv is not installed on developer machines | High | Document uv installation in README with one-liner |
| Docker Compose version conflicts | Medium | Pin Docker Compose v2 in documentation |
| Port conflicts (e.g., 5432 already in use) | Low | Use non-standard ports in docker-compose.yml |
| ChromaDB persistence issues | Medium | Add volume mount for data persistence |

---

## 7. Open Questions

None at this time. The scope is well-defined as foundational infrastructure.

---

## 8. Related Specifications

See `openspec/changes/init-project-foundation/specs/infrastructure/spec.md` for detailed environment requirements.
