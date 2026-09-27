# Smart Saver Bot

An intelligent, economy-focused shopping bot for the [Bale](https://www.bale.ai/) messenger.
Smart Saver Bot uses product and price data from the OKALA store to — in future phases —
help users assemble an economically optimized shopping basket within a given budget.

## Current Status

**Phase 3 — OKALA Data Source Investigation & Provider**

Phase 2's backend core (FastAPI app, async PostgreSQL/Redis, centralized exceptions,
Alembic) is unchanged. This phase adds `OkalaProviderInterface` (`app/scrapers`) — a
stable, provider-agnostic abstraction for categories/products/product-detail — and a
concrete adapter built against the generic `schema.org/Product` structured-data
contract, since no official OKALA API or feed could be confirmed and the live site
could not be fetched to verify its own markup. See
[docs/okala-research.md](docs/okala-research.md) for the full investigation (clearly
labeled Verified/Observed/Unknown) and its explicit follow-ups, and
[docs/architecture-decisions.md](docs/architecture-decisions.md) for earlier phases.
No business logic beyond this data-provider boundary (search, basket optimization, the
Bale bot itself, etc.) is implemented yet — see the [Roadmap](#roadmap) below.

## Architecture

Smart Saver Bot is built as a **Modular Monolith** with a **layered / service-oriented**
architecture. A single deployable application is organized into clearly bounded modules
(one package per concern, with an explicit interface), so that a module can be split out
into its own service later without a rewrite — while avoiding the operational overhead of
microservices at the current scale.

```text
User (Bale messenger)                          Future: public API (e.g. mobile app)
      ↓                                                     ↓
  Bale Bot (Phase 5+)                                 app/api  (FastAPI routers)
      ↓                                                     ↓
                    Application / Service Layer (Phase 3+)
      (User Mgmt, Search, Product, Basket Optimization,
       Recommendation, Price Analysis, Notification)
      ↓
  Repositories  ⇄  OKALA Data Provider (Phase 3+)  ⇄  Scheduler / Background Jobs
      ↓
  app/database  →  PostgreSQL (SQLAlchemy Async)  +  Redis (async client)
```

Business logic in the Service layer never talks to Bale or OKALA directly; both are
reached only through adapters (the Bot layer and the Data Provider layer, respectively),
so either can be swapped or extended without touching core logic. The Backend Core built
in this phase (`app/main.py`, `app/core`, `app/database`, `app/api`) is deliberately
independent of that future bot/business logic, so a general-purpose API can be added later
without changing it — see `docs/architecture-decisions.md`, ADR-006.

### Request flow

```text
Client
   │
   ▼
FastAPI (app/main.py)
   │
   ├── API / Routers (app/api)         → GET /health
   │
   ├── Centralized Exception Handling (app/core/exceptions.py)
   │
   └── Core Configuration (app/core/config.py, Pydantic Settings)
          │
          ├── PostgreSQL (app/database/session.py)
          │      └── SQLAlchemy Async engine + AsyncSession
          │
          └── Redis (app/database/redis.py)
                 └── redis.asyncio client
```

## Project Structure

```text
smart-saver-bot/
├── app/
│   ├── api/              # HTTP-facing layer
│   │   ├── health.py      # GET /health
│   │   └── router.py       # top-level router, included by main.py
│   ├── bot/                # Bale bot entry point (future)
│   ├── core/
│   │   ├── config.py        # Pydantic Settings — single config source of truth
│   │   └── exceptions.py    # exception hierarchy + FastAPI exception handlers
│   ├── database/
│   │   ├── base.py           # shared SQLAlchemy declarative Base
│   │   ├── session.py        # async engine, AsyncSession, check_database()
│   │   └── redis.py           # async Redis client, check_redis()
│   ├── models/              # ORM entities (future)
│   ├── schemas/
│   │   └── health.py         # /health response schema
│   ├── services/             # business logic (future)
│   ├── repositories/         # data-access abstractions (future)
│   ├── optimizers/            # basket optimization algorithm (future)
│   ├── scrapers/               # OKALA data provider adapter (future)
│   ├── utils/                 # shared helpers
│   └── main.py                 # FastAPI application factory + entry point
├── alembic/                     # database migrations (async)
│   ├── env.py
│   └── versions/
├── alembic.ini
├── docker-compose.yml            # local PostgreSQL + Redis for dev/test
├── tests/
│   ├── unit/                      # no external dependency
│   └── integration/                # real PostgreSQL + Redis required
├── scripts/
├── docs/
│   └── architecture-decisions.md
└── .github/workflows/ci.yml
```

## Requirements

- Python 3.12+
- [Poetry](https://python-poetry.org/) 1.8+
- Git
- PostgreSQL 16 and Redis 7 (for running the app or the integration tests — via
  `docker-compose.yml`, or any local install)

## Installation

```bash
git clone <repository-url>
cd smart-saver-bot
poetry install
cp .env.example .env
```

Edit `.env` and fill in real values. `DATABASE_URL` and `REDIS_URL` are required for the
app to report a healthy `/health`; `BALE_BOT_TOKEN` is not needed until Phase 5.

## Environment Variables

See [`.env.example`](.env.example) for the full list and default values.

| Variable                 | Used by                                | Required |
| ------------------------- | --------------------------------------- | -------- |
| `ENVIRONMENT`              | `app/core/config.py`                     | No (defaults to `development`) |
| `APP_NAME` / `APP_VERSION` | OpenAPI metadata                          | No |
| `DEBUG`                    | Error verbosity; **must be `false` in production** (enforced at startup) | No |
| `BALE_BOT_TOKEN`           | Bot layer (Phase 5+)                      | No |
| `DATABASE_URL`             | `app/database/session.py`                | For `/health` to report the database healthy |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` / `DATABASE_POOL_TIMEOUT` | connection pool tuning | No |
| `REDIS_URL`                | `app/database/redis.py`                  | For `/health` to report the cache healthy |
| `REDIS_TIMEOUT`            | Redis operation timeout                   | No |

None of these are ever hardcoded — see `docs/architecture-decisions.md`, ADR-006, and
[Security](#security) below.

## Running Locally

Start PostgreSQL and Redis (either is fine):

```bash
docker compose up -d          # brings up postgres:16 + redis:7, and creates
                               # both the dev (shopping_bot) and test
                               # (shopping_bot_test) databases
```

Apply migrations, then run the app:

```bash
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

## Swagger / OpenAPI

With the app running: interactive docs at <http://localhost:8000/docs>, raw schema at
<http://localhost:8000/openapi.json>.

## Health Endpoint

```bash
curl http://localhost:8000/health
```

Returns HTTP 200 with `{"status": "healthy", "database": "healthy", "cache": "healthy"}`
when both dependencies are reachable, or HTTP 503 with `"status": "degraded"` and the
specific component(s) marked `"unhealthy"` otherwise. It never raises an unhandled
exception, even if PostgreSQL/Redis are completely unreachable.

## PostgreSQL

Access is exclusively through SQLAlchemy's async engine (`app/database/session.py`) —
no raw `psycopg2`/sync calls, no ad-hoc connections elsewhere in the codebase. The engine
and session factory are built lazily (first use, not at import time) and are configurable
via `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT`.

## Redis

Access is exclusively through `redis.asyncio` (`app/database/redis.py`), built lazily the
same way, with `REDIS_TIMEOUT` bounding both connect and socket operations.

## Alembic / Database Migrations

```bash
poetry run alembic upgrade head        # apply all migrations
poetry run alembic downgrade base      # roll back to empty
poetry run alembic revision -m "add product table"   # new manual migration
poetry run alembic revision --autogenerate -m "..."   # once models exist (Phase 3+)
poetry run alembic current             # show current revision
poetry run alembic history             # show migration history
```

`alembic/env.py` reads `DATABASE_URL` from the same `app.core.config.Settings` the
application uses — there is no separate, second connection string anywhere in
`alembic.ini`.

## Testing

```bash
poetry run pytest                 # everything (unit + integration)
poetry run pytest tests/unit      # unit only — no external services needed
poetry run pytest -m integration  # integration only — needs PostgreSQL + Redis running
```

## Integration Testing

Integration tests (`tests/integration/`) run against a **real** PostgreSQL and Redis —
nothing is mocked. They use a dedicated test database (`shopping_bot_test`) and a
dedicated Redis logical database (`/15`) so they never touch development data. Start them
with `docker compose up -d` (see above) before running `pytest`.

## Docker / Test Services

`docker-compose.yml` provides local PostgreSQL and Redis for development and testing. It
is **not** a production deployment manifest (see `docs/architecture-decisions.md`,
ADR-011) — production deployment is Phase 12's concern.

## Linting

```bash
poetry run ruff check .
```

## Formatting

```bash
poetry run black .
```

## Type Checking

```bash
poetry run mypy app/
```

## Pre-commit

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## CI

`.github/workflows/ci.yml` runs Ruff, Black (check mode), MyPy, `alembic upgrade head`,
and the full Pytest suite (unit + integration) on every push and pull request against
`main` or `develop`, using temporary `postgres:16` and `redis:7` GitHub Actions services.
No real secret (e.g. `BALE_BOT_TOKEN`) is required or configured in CI.

## Security

- All secrets (`DATABASE_URL`, `REDIS_URL`, `BALE_BOT_TOKEN`) come exclusively from
  environment variables — never hardcoded, never logged.
- Database access uses SQLAlchemy's parameterized query APIs exclusively; no string
  concatenation into SQL.
- API error responses are structured and generic (`{"error": {"code": ..., "message":
  ...}}`); internal tracebacks, credentials, and connection strings never reach the
  client — see `app/core/exceptions.py`.
- `DEBUG=true` is rejected at startup when `ENVIRONMENT=production`.
- See `docs/architecture-decisions.md` for the full reasoning behind each of these.

## Git Workflow

| Branch          | Purpose                                                              |
| ---------------- | --------------------------------------------------------------------- |
| `main`           | Stable, deployable code. Updated only via reviewed Pull Request.      |
| `develop`        | Integration branch for completed work; base for every feature branch.|
| `feature/*`      | One feature or phase (e.g. `feature/backend-core`).                   |
| `fix/*`          | Non-critical bug fixes against `develop`.                            |
| `hotfix/*`       | Urgent fixes against `main`/production.                              |

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Roadmap

Phase 3 is one of 15 planned phases (Phase 0 – Phase 14). Immediately next:

- **Phase 4 — Product search**: Persian text normalization, fuzzy search, and the
  initial catalog sync job that populates the database from `OkalaProviderInterface`.

Later phases add basket optimization, the Bale bot itself, background
jobs, security hardening, deployment, and monitoring — in that order, per the project's
phased plan.

## License

See [`LICENSE`](LICENSE) — not yet finalized (project document does not specify one).
