"""Product search service (project document, chapter 13, Phase 4).

Two-stage search, per the Phase 4 architecture note: (1) exact match on
`Product.normalized_name`; (2) only if that yields nothing, PostgreSQL
`pg_trgm` fuzzy match with a configurable similarity threshold. Callers
never see SQL, `pg_trgm`, or the ORM session's query internals — those stay
inside `app.repositories.product_repository` (Phase 4 "keep database/search
concerns inside the appropriate layer").
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.catalog import Product
from app.repositories import product_repository as repo
from app.utils.persian_normalizer import normalize_text


class SearchService:
    """Free-text product search over the local, synced catalog.

    Takes an `AsyncSession` the same way `app.database.session.get_db_session`
    hands one to a FastAPI request — the service does not open its own.
    """

    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    async def search(self, query: str, *, limit: int | None = None) -> list[Product]:
        """Return product candidates for a free-text (Persian) query.

        Returns an empty list for a blank query, or for a normalized query
        shorter than `settings.search_min_query_length` once no exact match
        was found — a very short query produces too many low-quality
        `pg_trgm` matches to be useful (project document, Phase 4 risk:
        "کیفیت پایین تطبیق فازی برای عبارات بسیار کوتاه").
        """

        normalized_query = normalize_text(query)
        if not normalized_query:
            return []

        effective_limit = limit if limit is not None else self._settings.search_max_results

        exact_matches = await repo.find_by_normalized_name(self._session, normalized_query)
        if exact_matches:
            return exact_matches[:effective_limit]

        if len(normalized_query) < self._settings.search_min_query_length:
            return []

        return await repo.find_by_similarity(
            self._session,
            normalized_query,
            threshold=self._settings.search_similarity_threshold,
            limit=effective_limit,
        )
