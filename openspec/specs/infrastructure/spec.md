# Specification: Infrastructure Foundation

**Capability**: Infrastructure Foundation
**Version**: 1.0
**Status**: Proposed

---

## ADDED Requirements

### Requirement: Python Project Structure (REQ-INFRA-001)

The project MUST follow the directory structure defined in `openspec/project.md`:

```
/app
  /api          # FastAPI Routes
  /core         # Config & Security
  /models       # Pydantic & SQLModel Schemas
  /services     # External Integrations (CV, Chroma, MinIO)
  /worker       # Celery Tasks
/data           # Static JSONs (Taxonomy, etc.)
/scripts        # Utility scripts (doctor.py, etc.)
```

#### Scenario: Directory Structure Verification

**WHEN** a developer lists the project root directory
**THEN** the following directories MUST exist:
- `/app` containing subdirectories: `api`, `core`, `models`, `services`, `worker`
- `/data` for static assets
- `/scripts` for utility scripts

**AND** each directory MUST contain an `__init__.py` file (except `/data` and `/scripts`)

---

### Requirement: Package Management with uv (REQ-INFRA-002)

The project MUST use `uv` as the exclusive package manager.

**Acceptance Criteria**:
- `pyproject.toml` exists in project root with valid `[project]` section
- `uv.lock` is committed to version control
- All dependencies are declared in `pyproject.toml` under `[project.dependencies]`
- Dev dependencies are under `[project.optional-dependencies]`

**Violation**: Using `pip install` or `requirements.txt` is a critical failure.

#### Scenario: Dependency Installation

**GIVEN** a fresh clone of the repository
**WHEN** a developer runs `uv sync`
**THEN** all dependencies MUST install successfully
**AND** a `uv.lock` file MUST exist
**AND** `python -c "import fastapi; import celery"` MUST execute without errors

#### Scenario: Dependency Update

**WHEN** a developer adds a new dependency via `uv add package-name`
**THEN** `pyproject.toml` MUST be updated with the new package
**AND** `uv.lock` MUST be regenerated with locked versions

---

### Requirement: Multi-Stage Docker Build (REQ-INFRA-003)

The Dockerfile MUST use a multi-stage build pattern.

**Stage 1: Builder**
- Base image: `python:3.11-slim`
- Install `uv` via official installer
- Copy `pyproject.toml` + `uv.lock`
- Run `uv sync --frozen`
- Cache layer: MUST precede source code copying

**Stage 2: Runner**
- Base image: `python:3.11-slim`
- Copy virtual environment from builder
- Copy source code
- Set `PATH` to include venv binaries
- Set `PYTHONUNBUFFERED=1`

**Acceptance Criteria**:
- Final image size < 500MB
- Build completes in < 2 minutes on cached layers
- No build artifacts in final image

#### Scenario: Initial Docker Build

**GIVEN** the Dockerfile follows the multi-stage pattern
**WHEN** a developer runs `docker-compose build`
**THEN** the build MUST complete successfully
**AND** the final image size MUST be less than 500MB

#### Scenario: Cached Rebuild

**GIVEN** a previous successful build exists
**WHEN** a developer modifies only source code (not `pyproject.toml`)
**AND** runs `docker-compose build` again
**THEN** the build MUST complete in less than 60 seconds
**AND** the builder stage MUST use cached layers

---

### Requirement: Docker Compose Services (REQ-INFRA-004)

The `docker-compose.yml` MUST define the following services:

**Service 1: web (FastAPI)**
- Image: Built from Dockerfile
- Command: `uvicorn app.api.main:app --host 0.0.0.0 --port 8000`
- Ports: `8000:8000`
- Environment: Load from `.env`
- Depends on: `redis`, `db`
- Restart: `on-failure`

**Service 2: worker (Celery)**
- Image: Same as web
- Command: `celery -A app.worker.celery_app worker --loglevel=info`
- Environment: Load from `.env`
- Depends on: `redis`, `db`
- Restart: `on-failure`

**Service 3: redis (Celery Broker)**
- Image: `redis:7-alpine`
- Ports: `6379:6379`
- Volumes: `redis_data:/data`
- Restart: `always`

**Service 4: db (PostgreSQL)**
- Image: `postgres:15-alpine`
- Environment: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- Ports: `5433:5432` (avoid host port conflicts)
- Volumes: `postgres_data:/var/lib/postgresql/data`
- Restart: `always`

**Service 5: chroma (Vector DB)**
- Image: `chromadb/chroma:latest`
- Ports: `8001:8000`
- Volumes: `chroma_data:/chroma/chroma`
- Restart: `always`

#### Scenario: Service Startup

**GIVEN** a valid `docker-compose.yml` file
**WHEN** a developer runs `docker-compose up -d`
**THEN** all 5 services MUST start successfully
**AND** `docker-compose ps` MUST show all services as "Up"

#### Scenario: Service Dependencies

**WHEN** the web service starts
**THEN** it MUST wait for redis and db services to be healthy
**AND** NOT crash due to dependency unavailability

---

### Requirement: Pydantic Settings Configuration (REQ-INFRA-005)

The file `app/core/config.py` MUST define a `Settings` class inheriting from `pydantic_settings.BaseSettings`.

**Required Fields**:
```python
class Settings(BaseSettings):
    # Application
    app_name: str = "Smart Agriculture"
    debug: bool = False

    # Database
    database_url: str

    # Redis
    redis_url: str

    # OpenAI (for LangChain)
    openai_api_key: str

    # ChromaDB
    chroma_host: str = "chroma"
    chroma_port: int = 8000

    class Config:
        env_file = ".env"
```

**Acceptance Criteria**:
- All settings have type hints
- Default values are provided for non-sensitive fields
- `.env` file is ignored by git
- `.env.example` template is provided

#### Scenario: Environment Variable Loading

**GIVEN** a `.env` file with `DATABASE_URL=postgresql://user:pass@localhost/db`
**WHEN** the application loads settings via `Settings()`
**THEN** `settings.database_url` MUST equal the value from `.env`

#### Scenario: Configuration Validation

**WHEN** a required environment variable is missing
**THEN** `Settings()` MUST raise a `ValidationError` on initialization
**AND** the error message MUST clearly indicate which variable is missing

---

### Requirement: Health Check Script (REQ-INFRA-006)

The file `scripts/doctor.py` MUST verify connectivity to:

1. Python environment (version check)
2. PostgreSQL database (connection test)
3. Redis (ping test)
4. ChromaDB (HTTP health check)

**Exit Behavior**:
- Return code 0 if all checks pass
- Return code 1 if any check fails
- Print clear error messages for failures

#### Scenario: All Systems Healthy

**GIVEN** all infrastructure services are running
**WHEN** a developer runs `python scripts/doctor.py`
**THEN** the script MUST exit with code 0
**AND** print "All systems operational" or similar success message

#### Scenario: Database Connection Failure

**GIVEN** the PostgreSQL service is not running
**WHEN** a developer runs `python scripts/doctor.py`
**THEN** the script MUST exit with code 1
**AND** print a clear error message indicating database connection failed

---

## MODIFIED Requirements

None (this is a net-new capability).

---

## Non-Functional Requirements

### NFR-INFRA-001: Startup Time

FastAPI web service MUST be ready within 5 seconds.
Celery worker MUST be ready within 10 seconds.

#### Scenario: Web Service Startup

**WHEN** the web container starts
**THEN** it MUST accept HTTP requests within 5 seconds of container start

### NFR-INFRA-002: Resource Limits

- Web container: max 512MB RAM
- Worker container: max 1GB RAM
- Redis: max 256MB RAM
- Postgres: max 512MB RAM
- Chroma: max 512MB RAM

#### Scenario: Resource Constraint Enforcement

**WHEN** services are defined in docker-compose.yml
**THEN** each service MUST have resource limits specified
**AND** containers MUST NOT exceed allocated RAM limits

### NFR-INFRA-003: Configuration Security

- `.env` file MUST be in `.gitignore`
- `.env.example` MUST use placeholder values (e.g., `your-api-key-here`)
- No secrets in `docker-compose.yml` (use environment file reference)

#### Scenario: Secret Protection

**WHEN** a developer runs `git status`
**THEN** `.env` MUST NOT appear in untracked files
**AND** `.gitignore` MUST contain an entry for `.env`

---

## Dependencies

### External Dependencies
- Docker Engine >= 20.10
- Docker Compose >= 2.0
- Python >= 3.11

### Internal Dependencies
- None (this is the foundation layer)

---

## Compliance

This specification MUST comply with:
- `openspec/project.md` (Architecture Rules)
- `openspec/AGENTS.md` (Iron Triangle principles)
