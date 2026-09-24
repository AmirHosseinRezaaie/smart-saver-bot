# Smart Saver Bot

An intelligent, economy-focused shopping bot for the [Bale](https://www.bale.ai/) messenger.
Smart Saver Bot uses product and price data from the OKALA store to — in future phases —
help users assemble an economically optimized shopping basket within a given budget.

## Current Status

**Phase 1 — Repository & Architecture Bootstrap**

This phase establishes the project's standard structure, code-quality tooling, and the
skeleton of a layered architecture. No business logic (search, basket optimization,
OKALA integration, the Bale bot itself, etc.) is implemented yet — see
[docs/architecture-decisions.md](docs/architecture-decisions.md) for why, and the
[Roadmap](#roadmap) below for what comes next.

## Architecture

Smart Saver Bot is built as a **Modular Monolith** with a **layered / service-oriented**
architecture. A single deployable application is organized into clearly bounded modules
(one package per concern, with an explicit interface), so that a module can be split out
into its own service later without a rewrite — while avoiding the operational overhead of
microservices at the current scale.

```text
User (Bale messenger)
      ↓
  Bale Bot                (webhook / long polling)
      ↓
  Bot Handler             (command dispatch, conversation state)
      ↓
  Application / Service Layer
      (User Mgmt, Search, Product, Basket Optimization,
       Recommendation, Price Analysis, Notification)
      ↓
  Repositories  ⇄  OKALA Data Provider  ⇄  Scheduler / Background Jobs
      ↓
  PostgreSQL (source of truth) + Redis (cache / queue)
```

Business logic in the Service layer never talks to Bale or OKALA directly; both are
reached only through adapters (the Bot layer and the Data Provider layer, respectively),
so either can be swapped or extended without touching core logic.

## Project Structure

```text
smart-saver-bot/
├── app/
│   ├── api/            # HTTP-facing layer (future)
│   ├── bot/             # Bale bot entry point (future)
│   ├── core/            # Configuration and cross-cutting concerns
│   │   └── config.py
│   ├── models/          # ORM entities (future)
│   ├── schemas/         # Data-shape / validation definitions (future)
│   ├── services/        # Business logic (future)
│   ├── repositories/    # Data-access abstractions (future)
│   ├── optimizers/       # Basket optimization algorithm (future)
│   ├── scrapers/          # OKALA data provider adapter (future)
│   ├── database/        # PostgreSQL / Redis wiring (future)
│   ├── utils/           # Shared helpers
│   └── main.py           # Application entry point (Phase 1 smoke target)
├── tests/
│   └── test_smoke.py
├── scripts/
├── docs/
│   └── architecture-decisions.md
└── .github/workflows/ci.yml
```

## Requirements

- Python 3.12+
- [Poetry](https://python-poetry.org/) 1.8+
- Git

## Installation

```bash
git clone <repository-url>
cd smart-saver-bot
poetry install
cp .env.example .env
```

Edit `.env` and fill in real values as later phases require them (Phase 1 does not require
any of them to be set).

## Environment Variables

See [`.env.example`](.env.example) for the full list. None of these are read with a
hardcoded fallback value, and none are required for Phase 1's smoke test to pass:

| Variable          | Used by                          |
| ----------------- | --------------------------------- |
| `BALE_BOT_TOKEN`  | Bot layer (Phase 2+)              |
| `DATABASE_URL`    | Database layer (Phase 2+)         |
| `REDIS_URL`       | Cache / queue layers (Phase 2+)   |
| `ENVIRONMENT`     | `app/core/config.py` (Phase 1)    |

## Development

Run the entry point directly:

```bash
poetry run python -m app.main
```

## Testing

```bash
poetry run pytest
```

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

`.github/workflows/ci.yml` runs Ruff, Black (check mode), MyPy, and Pytest on every push
and pull request against `main` or `develop`. It has no dependency on any live external
service — everything it checks runs against the repository alone.

## Git Workflow

| Branch          | Purpose                                                              |
| ---------------- | --------------------------------------------------------------------- |
| `main`           | Stable, deployable code. Updated only via reviewed Pull Request.      |
| `develop`        | Integration branch for completed work; base for every feature branch.|
| `feature/*`      | One feature or phase (e.g. `feature/project-bootstrap`).              |
| `fix/*`          | Non-critical bug fixes against `develop`.                            |
| `hotfix/*`       | Urgent fixes against `main`/production.                              |

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Roadmap

Phase 1 is one of 15 planned phases (Phase 0 – Phase 14). Immediately next:

- **Phase 2 — Backend Core**: FastAPI application skeleton, health-check endpoint, async
  PostgreSQL connection via SQLAlchemy, Redis connection for caching.

Later phases add product search, basket optimization, the OKALA data provider, the Bale
bot itself, background jobs, security hardening, deployment, and monitoring — in that
order, per the project's phased plan.

## License

See [`LICENSE`](LICENSE) — not yet finalized (project document does not specify one).
