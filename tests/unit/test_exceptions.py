"""Unit tests for `app.core.exceptions`.

These build a minimal, throwaway FastAPI app wired only with the
centralized exception handlers, and drive it with an in-process
`TestClient` — no network, database, or Redis involved.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import (
    ApplicationException,
    CacheException,
    ConfigurationException,
    DatabaseException,
    register_exception_handlers,
)


class _Payload(BaseModel):
    budget: int


def _build_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/application")
    def boom_application() -> None:
        raise ApplicationException("generic application failure")

    @app.get("/boom/configuration")
    def boom_configuration() -> None:
        raise ConfigurationException("missing setting")

    @app.get("/boom/database")
    def boom_database() -> None:
        raise DatabaseException("db unreachable")

    @app.get("/boom/cache")
    def boom_cache() -> None:
        raise CacheException("cache unreachable")

    @app.get("/boom/unexpected")
    def boom_unexpected() -> None:
        raise RuntimeError("something nobody anticipated, with a secret token=abc123")

    @app.post("/validate")
    def validate(payload: _Payload) -> dict[str, int]:
        return {"budget": payload.budget}

    @app.get("/boom/http")
    def boom_http() -> None:
        raise HTTPException(status_code=404, detail="thing not found")

    return app


def test_application_exception_maps_to_its_status_code_and_body() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/boom/application")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "APPLICATION_ERROR"
    assert body["error"]["message"] == "generic application failure"


def test_configuration_exception_maps_correctly() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/boom/configuration")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "CONFIGURATION_ERROR"


def test_database_exception_maps_to_503() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/boom/database")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_ERROR"


def test_cache_exception_maps_to_503() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/boom/cache")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CACHE_ERROR"


def test_unhandled_exception_returns_generic_safe_message_without_leaking_details() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/boom/unexpected")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An internal error occurred."
    # The secret-looking token from the raised exception must never
    # reach the client, and neither must a raw traceback.
    raw_text = response.text
    assert "token=abc123" not in raw_text
    assert "Traceback" not in raw_text
    assert "RuntimeError" not in raw_text


def test_request_validation_error_returns_structured_details() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.post("/validate", json={"budget": "not-a-number"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)
    assert body["error"]["details"]


def test_http_exception_is_mapped_through_the_same_error_shape() -> None:
    """A `HTTPException` raised by application code (the realistic case —
    as opposed to Starlette's own internal 404 for an unmatched route,
    which this app never raises itself) goes through the same
    structured error shape as every other handled exception.
    """

    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/boom/http")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["error"]["message"] == "thing not found"
