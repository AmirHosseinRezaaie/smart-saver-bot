# Smart Saver Bot

An intelligent, economy-focused shopping bot for the **Bale** messenger, designed to help users make more economical shopping decisions using product, price, discount, and availability data.

The project follows a **Modular Monolith + Layered Architecture** and is being developed incrementally through a defined multi-phase roadmap.

---

## Current Status

**Phase 3 — OKALA Data Source Investigation & Provider Layer**

Phase 1 established the project structure, development tooling, repository conventions, and architectural foundation.

Phase 2 introduced the backend core, including:

- FastAPI application
- Environment-based configuration
- Async PostgreSQL access with SQLAlchemy
- Async Redis access
- Centralized exception handling
- Alembic migration infrastructure
- Integration and unit testing
- GitHub Actions CI

Phase 3 introduces the external data-provider boundary for OKALA and establishes a provider-agnostic interface for the rest of the application.

### Phase 3 includes

- Technical investigation of the OKALA data source
- `OkalaProviderInterface`
- Concrete `OkalaProvider` adapter
- `schema.org/Product` JSON-LD extraction
- Provider-to-internal data mapping
- Bounded asynchronous HTTP client
- Timeout and retry handling
- Request throttling
- Raw response snapshot support
- Provider-specific exception handling
- OKALA configuration through environment variables
- Unit tests for provider behavior, mapping, HTTP handling, and snapshots
- Documentation of verified findings, unknowns, limitations, and future migration paths

> **Important:** The live OKALA website could not be independently validated during this phase. Therefore, the provider is intentionally implemented against the standard `schema.org/Product` structured-data contract rather than an invented OKALA-specific API or unverified HTML structure. Live production compatibility remains an explicit follow-up.

See [`docs/okala-research.md`](docs/okala-research.md) for the complete investigation.

---

## Architecture

Smart Saver Bot is designed as a **Modular Monolith** with a layered / service-oriented architecture.

```text
                         ┌──────────────────────┐
                         │    Bale Messenger    │
                         │       Phase 5+       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     Bot / Handler    │
                         │       Phase 5+       │
                         └──────────┬───────────┘
                                    │
                                    ▼
              ┌────────────────────────────────────────┐
              │        Application / Service Layer     │
              │                                        │
              │ Search │ Product │ Basket │ Recommend │
              │ Price  │ User    │ Notify │ Analysis  │
              └───────────────────┬────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
                    ▼                            ▼
          ┌──────────────────┐        ┌──────────────────┐
          │   Repositories   │        │  Data Provider   │
          │                  │        │    Interface     │
          └────────┬─────────┘        └────────┬─────────┘
                   │                           │
                   │                  ┌────────▼─────────┐
                   │                  │   OkalaProvider  │
                   │                  │    Adapter       │
                   │                  └────────┬─────────┘
                   │                           │
                   │                  JSON-LD / External
                   │                  Data Source
                   │
                   ▼
          ┌──────────────────┐
          │    PostgreSQL    │
          │   Source of Truth│
          └──────────────────┘

                    ┌──────────────────┐
                    │      Redis       │
                    │ Cache / Jobs     │
                    └──────────────────┘
```

The Service layer is intentionally isolated from external providers.

Business logic must depend on `OkalaProviderInterface`, not directly on HTTP, HTML, JSON-LD, or a specific external API.

This allows a future official OKALA API adapter or another store provider to be introduced without rewriting the application layer.

---

## Phase 3 Provider Architecture

```text
External Data Source
        │
        ▼
┌────────────────────────┐
│   BoundedHttpClient    │
│                        │
│ Timeout                │
│ Retry / Backoff        │
│ Request Throttling     │
│ Error Translation      │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│     OkalaProvider      │
│                        │
│ fetch_categories()     │
│ fetch_products()       │
│ fetch_product_detail() │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│      JSON-LD Parser    │
│   schema.org/Product   │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│        Mapping         │
│                        │
│ Category               │
│ RawProduct             │
│ RawProductDetail       │
└───────────┬────────────┘
            │
            ▼
     Application Layer
```

---

## Project Structure

```text
smart-saver-bot/
│
├── app/
│   ├── api/
│   │   ├── health.py
│   │   └── router.py
│   │
│   ├── bot/
│   │   └── # Bale bot - Phase 5+
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   │
│   ├── database/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── redis.py
│   │
│   ├── models/
│   │
│   ├── schemas/
│   │   ├── catalog.py
│   │   ├── health.py
│   │   └── okala.py
│   │
│   ├── services/
│   │
│   ├── repositories/
│   │
│   ├── optimizers/
│   │
│   ├── scrapers/
│   │   ├── http_client.py
│   │   ├── interfaces.py
│   │   ├── jsonld.py
│   │   ├── mapping.py
│   │   ├── okala_provider.py
│   │   └── snapshot.py
│   │
│   ├── utils/
│   │
│   └── main.py
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── docs/
│   ├── architecture-decisions.md
│   └── okala-research.md
│
├── scripts/
│
├── tests/
│   ├── integration/
│   └── unit/
│       ├── test_config.py
│       ├── test_exceptions.py
│       ├── test_okala_http_client.py
│       ├── test_okala_mapping.py
│       ├── test_okala_provider.py
│       ├── test_okala_provider_from_settings.py
│       └── test_okala_snapshot.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
└── LICENSE
```

---

## Requirements

- Python 3.12+
- Poetry 1.8+
- Git
- PostgreSQL 16
- Redis 7

PostgreSQL and Redis can be started locally using Docker Compose.

---

## Installation

```bash
git clone <repository-url>
cd smart-saver-bot

poetry install

cp .env.example .env
```

Configure the required environment variables in `.env`.

---

## Running the Infrastructure

Start PostgreSQL and Redis:

```bash
docker compose up -d
```

Apply database migrations:

```bash
poetry run alembic upgrade head
```

Run the FastAPI application:

```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Interactive OpenAPI documentation:

```text
http://localhost:8000/docs
```

---

## Health Check

The backend exposes:

```http
GET /health
```

A healthy environment returns:

```json
{
  "status": "healthy",
  "database": "healthy",
  "cache": "healthy"
}
```

If PostgreSQL or Redis is unavailable, the endpoint reports a degraded state without exposing internal connection details.

---

# OKALA Data Provider

Phase 3 introduces a dedicated provider abstraction:

```python
class OkalaProviderInterface:
    async def fetch_categories(...)
    async def fetch_products(...)
    async def fetch_product_detail(...)
```

The application depends on this interface instead of directly depending on a specific HTTP endpoint or page structure.

### Supported provider operations

| Operation | Purpose |
|---|---|
| `fetch_categories()` | Retrieve available categories |
| `fetch_products()` | Retrieve products for a category |
| `fetch_product_detail()` | Retrieve detailed product information |

---

## Structured Data

The Phase 3 adapter processes structured JSON-LD data using the standard:

```text
schema.org/Product
```

The extraction layer supports:

- JSON-LD `<script>` blocks
- JSON arrays
- `@graph` structures
- `@type` filtering
- Product nodes
- Category / CollectionPage nodes

The mapping layer converts external structured data into provider-neutral Pydantic models.

---

## Provider Models

### Category

```text
external_id
name
parent_external_id
```

### RawProduct

```text
external_id
name
category_external_id
original_price
final_price
in_stock
url
```

### RawProductDetail

Extends `RawProduct` with:

```text
store_name
```

Fields whose availability cannot be guaranteed by the external source remain nullable.

---

## HTTP Reliability

The provider uses a bounded asynchronous HTTP client with:

- configurable timeout
- limited retry attempts
- exponential backoff
- retry handling for transient HTTP failures
- request throttling
- provider-specific exception translation

Retryable HTTP statuses include:

```text
408
429
500
502
503
504
```

Permanent errors are not retried unnecessarily.

---

## Raw Snapshots

The provider can optionally store raw response bodies for debugging and detecting upstream format changes.

Configuration:

```env
OKALA_SNAPSHOT_ENABLED=false
OKALA_SNAPSHOT_DIR=raw_snapshots
```

Snapshots are intentionally excluded from Git:

```gitignore
raw_snapshots/
```

Only response bodies are stored; request/response headers are not persisted.

---

## OKALA Investigation

The complete technical investigation is documented in:

```text
docs/okala-research.md
```

The report distinguishes between:

- Verified
- Observed
- Unknown / requires future confirmation

The investigation explicitly avoids:

- inventing undocumented OKALA endpoints
- bypassing access restrictions
- reverse-engineering private APIs without authorization
- assuming unverified HTML structures
- claiming live compatibility without evidence

### Current limitation

The live OKALA website could not be independently sampled during this phase.

Therefore:

```text
Provider abstraction        Implemented
JSON-LD adapter             Implemented
Mapping layer               Implemented
Retry / timeout             Implemented
Raw snapshots               Implemented
Unit tests                  Implemented
Live OKALA validation       Pending
```

Before production use, the actual OKALA access method and page/data contract must be confirmed.

---

## Environment Variables

Relevant Phase 3 settings:

| Variable | Purpose |
|---|---|
| `OKALA_PROVIDER_BASE_URL` | Explicit provider base URL |
| `OKALA_REQUEST_TIMEOUT` | HTTP request timeout |
| `OKALA_MAX_ATTEMPTS` | Maximum retry attempts |
| `OKALA_RETRY_BACKOFF` | Exponential backoff base |
| `OKALA_MIN_REQUEST_INTERVAL` | Minimum delay between requests |
| `OKALA_USER_AGENT` | Provider request User-Agent |
| `OKALA_SNAPSHOT_ENABLED` | Enable raw response snapshots |
| `OKALA_SNAPSHOT_DIR` | Snapshot storage directory |

`OKALA_PROVIDER_BASE_URL` intentionally has no hardcoded default.

This prevents the application from silently assuming an unverified external endpoint.

---

## Testing

Run the complete test suite:

```bash
poetry run pytest
```

Run only unit tests:

```bash
poetry run pytest tests/unit
```

Run integration tests:

```bash
poetry run pytest -m integration
```

Phase 3 adds dedicated unit coverage for:

- HTTP retry behavior
- HTTP error translation
- JSON-LD mapping
- category mapping
- product mapping
- product detail mapping
- provider behavior
- provider configuration
- raw snapshots

No automated CI test depends on the live OKALA website.

This keeps CI deterministic and avoids coupling the test suite to an external service.

---

## Code Quality

### Ruff

```bash
poetry run ruff check .
```

### Black

```bash
poetry run black .
```

### MyPy

```bash
poetry run mypy app/
```

### Pre-commit

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

---

## CI

GitHub Actions runs:

```text
Ruff
  ↓
Black
  ↓
MyPy
  ↓
Alembic migration
  ↓
Pytest
```

The CI environment uses temporary:

```text
PostgreSQL 16
Redis 7
```

No production secrets are required by the CI pipeline.

---

## Security

The project follows several security principles:

- No secrets are hardcoded.
- Environment variables are the single source of configuration.
- Production `DEBUG=true` is rejected.
- Internal exceptions are translated into safe API responses.
- Database access uses SQLAlchemy's parameterized APIs.
- Provider requests use bounded retries and explicit timeouts.
- Raw snapshots exclude request/response headers.
- Raw snapshots are excluded from Git.
- Unverified external endpoints are never silently assumed.

See:

```text
SECURITY.md
docs/architecture-decisions.md
```

for additional security and architectural decisions.

---

## Git Workflow

The project uses:

```text
main
  │
  └── stable / production

develop
  │
  ├── feature/backend-core
  ├── feature/okala-data-provider
  ├── feature/product-search
  └── ...
```

Feature branches follow:

```text
feature/<feature-name>
```

Phase 3 branch:

```text
feature/okala-data-provider
```

Commits follow the Conventional Commits specification.

Examples:

```text
feat: implement okala provider adapter
feat: map raw okala data to internal models
test: add provider mapping unit tests
docs: document okala data source investigation findings
```

---

# Roadmap

The project is developed through the following phases:

| Phase | Description |
|---|---|
| Phase 0 | Analysis & Design |
| Phase 1 | Repository & Architecture Bootstrap |
| Phase 2 | Backend Core |
| **Phase 3** | **OKALA Data Provider** |
| Phase 4 | Product Search & Persian Text Processing |
| Phase 5 | Bale Bot Integration |
| Phase 6 | Basket Optimization |
| Phase 7 | Best Single Price & Product Comparison |
| Phase 8 | Database, Cache & Background Jobs |
| Phase 9 | Recommendation Engine |
| Phase 10 | Comprehensive Testing |
| Phase 11 | Security Hardening |
| Phase 12 | Docker & CI/CD Deployment |
| Phase 13 | Monitoring, Logging & Beta |
| Phase 14 | Production Release & Future Development |

---

## Next Phase

### Phase 4 — Product Search

The next major step is the product search layer.

Planned capabilities include:

- Persian text normalization
- tokenization
- fuzzy matching
- normalized product search
- catalog synchronization
- PostgreSQL search capabilities
- Search Service
- Search History

The Search Service will consume `OkalaProviderInterface` rather than depending directly on OKALA.

This preserves the architectural separation established in Phase 3.

---

## Future Capabilities

The long-term project roadmap includes:

- Economically optimized shopping baskets
- Budget-constrained product selection
- Product comparison
- Economic Score calculation
- Personalized recommendations
- Price and discount alerts
- Shopping lists
- Favorites
- Price history
- Multiple store providers
- Background synchronization
- Monitoring and observability
- Production deployment

---

## Documentation

Important project documentation:

```text
docs/
├── architecture-decisions.md
└── okala-research.md
```

Additional repository documentation:

```text
README.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md
CHANGELOG.md
```

---

## License

See [`LICENSE`](LICENSE).

The project license remains subject to final project configuration.