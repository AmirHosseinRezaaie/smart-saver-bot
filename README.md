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