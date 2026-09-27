"""External data provider / scraper layer.

The only package in the project allowed to know how OKALA data is
actually obtained (`OkalaProviderInterface` in `interfaces.py`, backed by
the `OkalaProvider` adapter in `okala_provider.py`). See
`docs/okala-research.md` for the investigation behind the chosen access
method, and `app/core/config.py` for its configuration.
"""
