# Smart Agriculture - Plant Disease and Pest Diagnosis System

A laboratory-scale intelligent diagnosis system for plant diseases and pests, combining Computer Vision (CV) with Retrieval-Augmented Generation (RAG).

## Features

- **CV Integration**: Connect to existing computer vision algorithms for pest/disease identification
- **RAG-powered Reports**: LangChain-based report generation using retrieved context from ChromaDB
- **Async Task Processing**: Celery workers handle heavy inference operations
- **Dynamic Templates**: Separate report formats for diseases vs pests
- **Health Monitoring**: Built-in health check script for all infrastructure components

## Quick Start

### Prerequisites

Ensure you have the following installed:

- **Python 3.12** ([Download](https://www.python.org/downloads/))
- **Docker Engine** >= 20.10 ([Install Guide](https://docs.docker.com/engine/install/))
- **Docker Compose** >= 2.0 ([Install Guide](https://docs.docker.com/compose/install/))
- **uv** package manager ([Install](https://github.com/astral-sh/uv))

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd Smart-Agriculture

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install Python dependencies
uv sync

# 4. Create environment file
cp .env.example .env
# Edit .env with your actual values (especially OPENAI_API_KEY)

# 5. Start infrastructure services
docker-compose up -d

# 6. Verify all systems are operational
python scripts/doctor.py
```

### Expected Output

If all checks pass, you should see:

```
🏥 Smart Agriculture System Health Check

Checking infrastructure components...

✓ Python version: 3.12.x
✓ Directory exists: app/
...
✓ All systems operational! (7/7 checks passed)
```

## Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | **FastAPI** | Async REST API |
| Task Queue | **Celery** + Redis | Background job processing |
| Database | **PostgreSQL** | Task persistence |
| Vector DB | **ChromaDB** | Semantic search for RAG |
| LLM Orchestration | **LangChain** | Report generation |
| Storage | **MinIO** | Image persistence |
| Package Manager | **uv** | Fast dependency management |

### System Flow

1. **Upload Image**: User uploads plant image via FastAPI
2. **Create Task**: System generates task ID and returns immediately
3. **CV Processing**: Celery worker calls CV algorithm
4. **Taxonomy Mapping**: Map class_id to standard Chinese name
5. **RAG Retrieval**: Query ChromaDB with diagnosis name
6. **Report Generation**: LangChain generates structured report
7. **Result Polling**: Frontend polls API for completion

### Project Structure

```
Smart-Agriculture/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Configuration & templates
│   ├── models/           # Pydantic & SQLModel schemas
│   ├── services/         # External integrations (CV, Chroma, MinIO)
│   └── worker/           # Celery tasks & chains
├── data/                 # Static JSON files (taxonomy, etc.)
├── scripts/              # Utility scripts (doctor.py)
├── openspec/             # OpenSpec change management
├── pyproject.toml        # Project metadata & dependencies
├── Dockerfile            # Multi-stage build
├── docker-compose.yml    # Service orchestration
└── README.md
```

## Configuration

### Environment Variables

Key environment variables (see `.env.example`):

```bash
# Application
APP_NAME=Smart Agriculture
DEBUG=false

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/smartag

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI (required for LLM features)
OPENAI_API_KEY=sk-your-key-here

# ChromaDB
CHROMA_HOST=chroma
CHROMA_PORT=8000

# MinIO (object storage)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

### Port Mappings

| Service | Container Port | Host Port |
|---------|---------------|-----------|
| FastAPI (Web) | 8000 | 8000 |
| Celery Worker | - | - (not exposed) |
| PostgreSQL | 5432 | 5434 |
| Redis | 6379 | 6379 |
| ChromaDB | 8000 | 8001 |
| MinIO | 9000 | 9000 |

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
uv run black app/ scripts/

# Lint code
uv run ruff check app/ scripts/

# Type checking
uv run mypy app/
```

### Adding Dependencies

```bash
# Add a new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name
```

### Docker Development

```bash
# Rebuild services after code changes
docker-compose up --build

# View logs for a specific service
docker-compose logs -f web
docker-compose logs -f worker

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

## Troubleshooting

### Issue: `uv sync` fails

**Solution**: Ensure you're using Python 3.12
```bash
python --version  # Should be 3.12.x
```

### Issue: PostgreSQL connection fails in doctor.py

**Solution**: Check if Docker services are running
```bash
docker-compose ps
docker-compose logs db
```

### Issue: Ports already in use

**Solution**: Either stop conflicting services or modify `docker-compose.yml` port mappings

### Issue: OpenAI API errors

**Solution**: Verify your API key in `.env`:
```bash
echo $OPENAI_API_KEY  # Should start with "sk-"
```

### Issue: ChromaDB connection timeout

**Solution**: ChromaDB takes time to start. Wait 30 seconds after `docker-compose up` before running health checks.

## OpenSpec Development

This project follows the **OpenSpec** specification-driven development workflow. See `openspec/AGENTS.md` for details.

To create a new change:

1. Create proposal: `openspec/changes/<change-id>/proposal.md`
2. Write spec: `openspec/changes/<change-id>/specs/<capability>/spec.md`
3. Define tasks: `openspec/changes/<change-id>/tasks.md`
4. Validate: `openspec validate <change-id>`
5. Implement following tasks.md

## License

MIT

## Contributing

1. Follow the [OpenSpec workflow](./openspec/AGENTS.md)
2. Ensure `python scripts/doctor.py` passes before committing
3. Keep dependencies up-to-date with `uv sync`
4. Write tests for new features

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Run `python scripts/doctor.py` to diagnose infrastructure issues
- Check service logs: `docker-compose logs <service-name>`
