## Phase 4 — Product Processing, Normalization & Search

Phase 4 introduces the product search layer of Smart Saver Bot.

The main objective of this phase is to make product search more tolerant of common Persian text variations and to provide a reliable local catalog search layer backed by PostgreSQL.

### Implemented Features

- Persian text normalization
- Persian/Arabic character normalization
- Persian, Arabic, and ASCII digit normalization
- Whitespace normalization
- Invisible/control character handling
- Basic tokenization
- Normalized product names
- Exact product search
- Fuzzy product search
- PostgreSQL `pg_trgm` integration
- Trigram-based product similarity
- Configurable similarity threshold
- Configurable minimum query length
- Configurable maximum search results
- Local product catalog synchronization
- Product upsert based on external identifiers
- Price snapshot storage
- Discount calculation and storage
- Partial failure handling during catalog synchronization

### Search Architecture

Product search follows a two-stage strategy:

```text
User Query
    ↓
Persian Text Normalizer
    ↓
Exact Search
    ↓
If no suitable result
    ↓
Fuzzy Search
    ↓
PostgreSQL + pg_trgm
    ↓
Ranked Product Results
```

This approach allows the system to return relevant products even when the user's input does not exactly match the stored product name.

### Persian Text Normalization

The normalizer converts common Persian and Arabic writing variations into a consistent representation.

Examples include:

- Arabic `ي` → Persian `ی`
- Arabic `ك` → Persian `ک`
- Persian/Arabic digits → normalized numeric representation
- repeated whitespace → single whitespace
- invisible characters → removed
- unnecessary punctuation → normalized/removed

The normalization process is designed to be deterministic and idempotent.

### Fuzzy Search

PostgreSQL `pg_trgm` is used to support fuzzy product matching without introducing a separate search engine.

The search layer supports configurable parameters such as:

```env
SEARCH_SIMILARITY_THRESHOLD=0.3
SEARCH_MIN_QUERY_LENGTH=2
SEARCH_MAX_RESULTS=20
```

The system first attempts an exact match against `normalized_name`.

If no suitable exact result is found and the query satisfies the fuzzy-search requirements, PostgreSQL trigram similarity is used to identify relevant products.

### Catalog Synchronization

Phase 4 also introduces the local catalog synchronization layer.

The synchronization flow is:

```text
OKALA Provider
      ↓
Catalog Sync Service
      ↓
Normalize Product Data
      ↓
Product Upsert
      ↓
Price Snapshot
      ↓
Discount Data
      ↓
PostgreSQL Catalog
```

Products are identified using their external provider identifiers so repeated synchronization does not create duplicate product records.

Price information is stored as snapshots to preserve price history for future features.

### Database Search

The catalog search layer uses PostgreSQL indexes to support both exact and fuzzy matching.

The fuzzy search infrastructure uses:

- PostgreSQL `pg_trgm`
- Trigram similarity
- GIN indexing for normalized product names

This keeps the MVP architecture relatively simple while providing a practical fuzzy-search capability.

### Testing

Phase 4 adds tests for the Persian normalization layer and search functionality.

The test coverage includes cases such as:

- Arabic/Persian character differences
- Persian and Arabic digits
- whitespace normalization
- invisible characters
- punctuation
- empty input
- tokenization
- normalization idempotency
- fuzzy product matching

Integration testing against PostgreSQL is required for validating the real `pg_trgm` behavior.

### Current Project Status

**Current Phase:** Phase 4 — Product Processing, Normalization & Search

**Completed foundation:**

- Phase 0 — Analysis & Design
- Phase 1 — Repository & Architecture
- Phase 2 — Backend Core
- Phase 3 — OKALA Data Provider
- Phase 4 — Product Processing, Normalization & Search

The next major development stage is the basket optimization engine.

### Next Phase

**Phase 5 — Basket Optimization Engine**

The next phase will build on the search and catalog infrastructure to implement:

- Economic Score
- Effective Price
- Basket optimization
- Budget constraints
- Mandatory products
- Greedy optimization
- Local search improvements
- Economical basket generation
=======
> An intelligent, economy-focused shopping assistant for the Bale messenger, designed to help users make better purchasing decisions using product, price, discount and availability data.

**Smart Saver Bot** is a modular Python backend project that aims to analyze shopping data from OKALA and help users build economically optimized shopping baskets within a defined budget.

The project is being developed incrementally through a structured multi-phase roadmap.

---

## 🚧 Current Status

**Phase 2 — Backend Core: Completed**

The current version provides a stable backend foundation built with:

- FastAPI
- PostgreSQL
- SQLAlchemy Async
- Redis
- Alembic
- Pydantic Settings
- Pytest
- Docker Compose
- GitHub Actions

The backend currently includes:

- A runnable FastAPI application
- Centralized configuration management
- PostgreSQL async connectivity
- Redis async connectivity
- Centralized exception handling
- Database migration infrastructure
- `/health` endpoint
- Unit and integration tests
- CI test execution

Business features such as OKALA integration, product search, basket optimization and Bale bot interaction are intentionally implemented in later phases.

---

## 🎯 Project Goal

The long-term goal is to build a shopping assistant that can:

1. Find economical products
2. Compare prices across available stores
3. Analyze discounts and effective prices
4. Build optimized shopping baskets within a budget
5. Handle mandatory products
6. Provide intelligent shopping recommendations
7. Eventually support additional stores and more advanced recommendation capabilities

The project uses an **Economic Score** rather than relying only on discount percentage when evaluating economic value.

---

## 🏗️ Architecture

Smart Saver Bot follows a **Modular Monolith + Layered / Service-Oriented Architecture**.

```text
                         ┌──────────────────────┐
                         │     Bale Messenger   │
                         │       Phase 5+       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      Bale Bot        │
                         │       Phase 5+       │
                         └──────────┬───────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│              Application / Service Layer                    │
│                                                             │
│ User │ Search │ Product │ Basket │ Recommendation │ Price  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │    Repositories     │
                 └──────────┬──────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌─────────────────┐         ┌──────────────────┐
     │ OKALA Provider  │         │ Background Jobs  │
     │    Phase 3+     │         │     Phase 8+     │
     └─────────────────┘         └──────────────────┘

                            │
                            ▼
                 ┌─────────────────────┐
                 │    Database Layer   │
                 │                     │
                 │ PostgreSQL + Redis  │
                 └─────────────────────┘
```

The architecture intentionally separates business logic from external systems such as Bale and OKALA.

This makes it possible to replace or extend external integrations without rewriting the core application logic.

---

## 📦 Current Backend Core

Phase 2 establishes the following foundation:

### FastAPI

The main application is exposed through:

```text
app/main.py
```

The API layer is organized under:

```text
app/api/
```

### Configuration

Application configuration is managed through:

```text
app/core/config.py
```

using Pydantic Settings and environment variables.

No production secrets are hardcoded into the source code.

### PostgreSQL

Database connectivity is implemented using:

```text
SQLAlchemy Async
asyncpg
```

The database infrastructure is located under:

```text
app/database/session.py
app/database/base.py
```

### Redis

Redis connectivity is implemented using the asynchronous Redis client:

```text
app/database/redis.py
```

Redis will later support caching and background-related infrastructure.

### Exception Handling

Centralized exception handling is implemented in:

```text
app/core/exceptions.py
```

Application errors are converted into consistent API responses without exposing internal implementation details.

### Database Migrations

Alembic is configured under:

```text
alembic/
```

Migrations can be managed using:

```bash
poetry run alembic upgrade head
```

---

## ❤️ Health Check

The backend exposes:

```http
GET /health
```

The endpoint checks the availability of:

- PostgreSQL
- Redis

Example healthy response:

```json
{
  "status": "healthy",
  "database": "healthy",
  "cache": "healthy"
}
```

If a dependency becomes unavailable, the endpoint reports a degraded state instead of exposing an unhandled server exception.

---

## 📁 Project Structure

```text
smart-saver-bot/
│
├── app/
│   ├── api/
│   │   ├── health.py
│   │   └── router.py
│   │
│   ├── bot/
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   │
│   ├── database/
│   │   ├── base.py
│   │   ├── redis.py
│   │   └── session.py
│   │
│   ├── models/
│   ├── optimizers/
│   ├── repositories/
│   ├── schemas/
│   │   └── health.py
│   ├── scrapers/
│   ├── services/
│   ├── utils/
│   └── main.py
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── docs/
│   └── architecture-decisions.md
│
├── scripts/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
└── README.md
```

---

## ⚙️ Requirements

Recommended development environment:

- Python 3.12+
- Poetry 1.8+
- PostgreSQL 16
- Redis 7
- Git
- Docker / Docker Compose

---

## 🚀 Installation

Clone the repository:

```bash
git clone <repository-url>
cd smart-saver-bot
```

Install dependencies:

```bash
poetry install
```

Create the environment configuration:

```bash
cp .env.example .env
```

Then configure the required environment variables in `.env`.

> Never commit `.env` or real credentials to Git.

---

## 🐳 Local Infrastructure

PostgreSQL and Redis can be started using Docker Compose:

```bash
docker compose up -d
```

This provides the local infrastructure required by the backend and integration tests.

---

## 🗄️ Database

Apply migrations:

```bash
poetry run alembic upgrade head
```

Check migration status:

```bash
poetry run alembic current
```

View migration history:

```bash
poetry run alembic history
```

Create a migration:

```bash
poetry run alembic revision -m "add product table"
```

---

## ▶️ Run the Application

Start the FastAPI development server:

```bash
poetry run uvicorn app.main:app --reload
```

The application will be available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

Health check:

```text
http://localhost:8000/health
```

---

## 🧪 Testing

Run the complete test suite:

```bash
poetry run pytest
```

Run unit tests:

```bash
poetry run pytest tests/unit
```

Run integration tests:

```bash
poetry run pytest tests/integration
```

Integration tests require PostgreSQL and Redis to be available.

The test suite currently covers:

- Configuration loading and validation
- Production debug restrictions
- Secret/configuration safety
- Centralized exception handling
- PostgreSQL connectivity
- Redis connectivity
- Health endpoint behavior

---

## 🔐 Security

Security is treated as a core project requirement.

### Secrets

Secrets must be provided through environment variables.

Never commit:

```text
.env
```

or real:

- Bale tokens
- Database credentials
- Redis credentials
- API keys
- Passwords

Only placeholder values belong in:

```text
.env.example
```

### Error Handling

Internal exceptions and sensitive implementation details must never be exposed directly to API clients.

### Production

Debug mode must be disabled in production.

---

## 🌿 Git Workflow

The project follows a structured branching strategy:

```text
main
  │
  └── develop
        │
        ├── feature/backend-core
        ├── feature/product-search
        ├── feature/basket-optimizer
        └── ...
```

### Branches

| Branch | Purpose |
|---|---|
| `main` | Stable production-ready code |
| `develop` | Integration branch |
| `feature/*` | Feature or phase development |
| `fix/*` | Non-critical bug fixes |
| `hotfix/*` | Urgent production fixes |

### Commit Convention

The project follows Conventional Commits.

Examples:

```text
feat: add async database connection
fix: handle unavailable products
test: add basket optimizer tests
docs: update project documentation
chore: configure github actions ci
refactor: extract economic score calculator
```

---

## 🗺️ Roadmap

The project is divided into independent development phases.

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Analysis & Design | ✅ Completed |
| Phase 1 | Repository & Base Architecture | ✅ Completed |
| Phase 2 | Backend Core | ✅ Completed |
| Phase 3 | OKALA Data Source Integration | 🔜 Next |
| Phase 4 | Product Processing & Search | Planned |
| Phase 5 | Bale Bot & User Interaction | Planned |
| Phase 6 | Basket Optimization | Planned |
| Phase 7 | Product Price Comparison | Planned |
| Phase 8 | Database, Cache & Background Jobs | Planned |
| Phase 9 | Recommendation Engine | Planned |
| Phase 10 | Comprehensive Testing | Planned |
| Phase 11 | Security Hardening | Planned |
| Phase 12 | Docker & CI/CD | Planned |
| Phase 13 | Monitoring & Beta | Planned |
| Phase 14 | Production Release | Planned |

---

## 🔮 Planned Core Capabilities

### 1. Economic Basket

Build an economically optimized basket within a user-defined budget range.

```text
Minimum Budget
      +
Maximum Budget
      ↓
Product Candidates
      ↓
Economic Score
      ↓
Basket Optimization
      ↓
Optimized Basket
```

### 2. Mandatory Products

Allow users to specify products that must be included in the basket before optimizing the remaining budget.

### 3. Best Price Search

Find economical options for a requested product across available data.

### 4. Product Comparison

Compare multiple products based on:

- Original price
- Final price
- Discount percentage
- Saving amount
- Store
- Availability
- Shipping cost

### 5. Smart Recommendations

A future rule-based recommendation engine will suggest shopping baskets based on user needs and budget.

---

## 🧠 Economic Score

The project does not consider the highest discount percentage as the only definition of an economical product.

The planned scoring model considers multiple factors, including:

- Discount percentage
- Discount amount
- Effective price
- Stock availability
- Shipping cost

This allows the optimizer to evaluate the actual economic value of a product rather than relying on a single metric.

---

## 📚 Documentation

Detailed technical documentation is maintained separately from the README.

Important documentation includes:

```text
docs/
├── architecture-decisions.md
└── ...
```

The complete project specification and development roadmap define the architecture, data model, optimization strategy, Git workflow, security requirements and development phases.

---

## 🤝 Contributing

Development guidelines are available in:

```text
CONTRIBUTING.md
```

Before submitting changes:

1. Create a feature branch.
2. Follow the Conventional Commit format.
3. Add or update tests where necessary.
4. Run the test suite.
5. Ensure no secrets are committed.
6. Open a Pull Request against `develop`.

---

## 📄 License

See:

```text
LICENSE
```

for licensing information.

---

## 📌 Project Status

**Current milestone: Phase 2 — Backend Core**

The backend foundation is now ready for the next development milestone:

**Phase 3 — OKALA Data Source Investigation & Integration**
