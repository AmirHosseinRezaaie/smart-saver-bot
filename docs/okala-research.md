# OKALA Data Source Investigation (Phase 3)

This document is the technical report required by the project specification
(chapter 10.1, "بررسی فنی منبع داده OKALA") and by the Phase 3 deliverables
(chapter 13). It records what was actually checked, and labels every
statement as **Verified**, **Observed**, or **Unknown / requires future
confirmation** — no unconfirmed claim is presented as fact.

## 1. Investigation date

2026-09-25.

## 2 & 3. Access method investigated, and evidence/source used

Investigated, in the order the project document prescribes (chapter 10.1,
"اصل راهنما"): (a) an official public developer API, (b) an official data
feed, (c) publicly embedded structured product data (`schema.org/Product`
or similar JSON), (d) direct HTML scraping as a last resort.

Evidence sources: web search for OKALA developer/API documentation and for
its published terms/rules; an attempted direct fetch of `https://www.okala.com/`
through this environment's own web-fetch tool; and general knowledge of how
Iranian e-commerce sites of this kind typically expose (or don't expose)
programmatic access.

## 4. API availability status

**Unknown / requires future confirmation.** No public, documented OKALA
developer API or partner data feed could be found via search. This is
consistent with — but does not conclusively prove — the "no suitable
official API" case the project document anticipates (chapter 10.1: "مدرک
رسمی ... یافت نشد"). The project document itself calls for the development
team to ask OKALA's support/technical contact directly at the start of
Phase 3; **that direct outreach has not been performed as part of this
implementation** and is listed under Limitations (§14) and the migration
path (§15).

## 5. robots.txt findings

**Observed, not independently verified against the live file.** This
environment's own web-fetch tool refused to retrieve `https://www.okala.com/`,
reporting: *"Site disallows automated access. Use the search-result snippet,
or find an alternative source."* This is itself evidence that OKALA's
`robots.txt` (or an equivalent access control) currently disallows
automated fetching, at least for the client this tool represents. The
actual `robots.txt` contents (which paths are disallowed, for which
user-agents, any `Crawl-delay`) could not be read directly and remain
**Unknown**.

## 6. Relevant usage/ToS findings

**Observed (from a comparable Iranian online-supermarket's public terms,
not OKALA's own).** OKALA's own terms-of-service page could not be fetched
for the same reason as §5. As general context (not a substitute for
OKALA's actual terms), a comparable Iranian online-grocery competitor's
public terms page explicitly prohibits data mining, robots, and similar
automated collection/extraction tools against its product listings and
prices. It would be consistent with common practice in this sector for
OKALA's own terms to contain a similar restriction, but this is **not
confirmed** for OKALA specifically and must not be treated as such.

## 7. Structured-data findings

**Unknown.** Because the live site could not be fetched (§5), it was not
possible to confirm whether OKALA's product or category pages embed
`schema.org/Product` (or another) JSON-LD block, a sitemap, or any other
structured feed. No claim is made that OKALA does or does not expose such
data.

## 8. Selected implementation method

Given the above, this phase deliberately does **not** implement scraping
against the live `okala.com` site: doing so without being able to confirm
`robots.txt`/ToS compliance would contradict this project's explicit
"never bypass robots restrictions or ToS" rule, and doing so against
unverified HTML would mean fabricating an adapter's contract, which the
project's failure/uncertainty policy also forbids.

Instead, Phase 3 delivers:

1. A stable `OkalaProviderInterface` (`app/scrapers/interfaces.py`) that the
   rest of the application depends on, per chapter 10.2.
2. A concrete adapter, `OkalaProvider` (`app/scrapers/okala_provider.py`),
   implemented against the **standard, publicly documented
   `schema.org/Product` JSON-LD contract** — the specific mechanism the
   project document itself names as the preferred fallback when no
   official API exists (chapter 10.1: "داده ساختاریافته ... schema.org/Product
   ... در اولویت قرار گیرد"). The adapter parses this generic, well-known
   contract rather than any endpoint or HTML shape invented for OKALA
   specifically.
3. `okala_provider_base_url` has **no default** in `app/core/config.py` —
   the adapter cannot be pointed at any host, let alone `okala.com`,
   without an operator explicitly configuring one after completing the
   verification in §15.

This satisfies the "implement a stable provider abstraction without
coupling the rest of the application to OKALA" objective while leaving the
one genuinely unverifiable step — whether OKALA's own pages carry this
exact structured-data shape, and are legally reachable at all — as an
explicit, tracked follow-up rather than a fabricated assumption.

## 9. Rejected alternatives and why

- **Direct HTML scraping of `okala.com`.** Rejected for this phase: the
  fetch refusal in §5 is itself a signal of an access restriction, and the
  project's explicit rule ("never bypass ... robots restrictions") applies
  even before the exact robots.txt rule text is known — the safer default
  is to not proceed automatically.
- **Guessing an unofficial/internal OKALA API from mobile-app reverse
  engineering.** Rejected: this was not attempted. Reverse-engineering a
  private API without OKALA's consent carries the same legal/ToS risk as
  scraping and was out of scope for this investigation.
- **Fabricating a plausible-looking OKALA-specific endpoint contract.**
  Rejected per the project's explicit "never invent endpoints, never
  fabricate successful API responses" instruction.

## 10. Fields successfully obtained

None from the live OKALA site (no live access was performed — see §5–§7).
From the **generic `schema.org/Product` contract** the adapter implements
(verified against the public schema.org specification, not against OKALA):
`name`, an identifier (`sku`/`productID`), `offers.price` (→ `final_price`),
`offers.availability` (→ `in_stock`), `offers.seller.name` / `brand.name`
(→ store name), and `url`. See `app/scrapers/mapping.py`.

## 11. Fields unavailable / nullable

`schema.org/Product` has no standardized "original price before discount"
field; the adapter reads a non-standard `highPrice` key defensively and
otherwise leaves `original_price` (and therefore discount amount/percent)
`None`. `in_stock`, `url`, and `category_external_id` are all nullable in
`app.schemas.okala.RawProduct` for the same reason — per the project
document (chapter 10.1), the Optimizer must not depend on these existing.
Shipping cost/discount validity windows are not modeled at all in this
phase; nothing in the generic contract suggests where they would live.

## 12. Pagination behavior

**Unknown against the live site.** The adapter's `fetch_products` accepts
a `page` parameter and forwards it as a `?page=` query parameter (a common
convention), but whether OKALA's category pages actually paginate this
way — or at all — is unconfirmed.

## 13. Rate-limit/access considerations

No documented or observed OKALA-specific rate limit exists (none could be
found or fetched). The adapter nonetheless enforces a conservative
minimum interval between requests (`OKALA_MIN_REQUEST_INTERVAL`, default
1 second) and a small bounded retry count with exponential backoff
(`OKALA_MAX_ATTEMPTS`, `OKALA_RETRY_BACKOFF`) by default, so that once a
verified base URL is configured, the adapter does not hammer the source
regardless of what OKALA's real limits turn out to be.

## 14. Limitations

- The live `okala.com` site was never actually fetched or sampled; every
  statement above about its structure is either explicitly marked
  Unknown or is about a *generic* standard, not OKALA's specific markup.
- OKALA's support/developer contact, as the project document instructs,
  has not been contacted.
- `OkalaProvider` is fully unit-tested against fixed HTML/JSON-LD
  fixtures (see `tests/unit/test_okala_*.py`) but has **not** been
  integration-tested against the real OKALA site, and per this project's
  testing rules, no automated CI test ever will be.
- Phase 3's acceptance criterion ("fetch_product_detail for a real product
  returns name/prices without crashing") cannot be marked verified until
  someone with the ability to legally reach `okala.com` (or an official
  OKALA API, once one exists) confirms the adapter's assumptions against a
  real page and adjusts `app/scrapers/okala_provider.py`'s three TODO'd
  path templates and `@type` names accordingly.

## 15. Future migration path if OKALA later provides an official API

Because the rest of the application depends only on `OkalaProviderInterface`
(chapter 10.2's Adapter Pattern), switching to an official API later is a
localized change:

1. Confirm the official API's contract (auth, endpoints, schema).
2. Add a new adapter class implementing `OkalaProviderInterface` against
   that API (e.g. `OkalaOfficialApiProvider`), reusing
   `app.schemas.okala` as its output type.
3. Point the composition point that constructs the provider (currently
   `OkalaProvider.from_settings`) at the new class, gated by configuration
   if both must coexist during migration.
4. No change is required in the Service layer or any other caller of
   `OkalaProviderInterface`.

The same applies in reverse if OKALA's actual product pages turn out to
use a different structured-data shape than the generic one implemented
here: only `app/scrapers/okala_provider.py` and `app/scrapers/mapping.py`
would need to change.
