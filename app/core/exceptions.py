"""Centralized exception hierarchy and FastAPI exception handlers.

Two things live here:

1. `ApplicationException` and its small set of subclasses — the
   vocabulary the rest of the application (config, database, cache,
   and future business-logic layers) raises instead of leaking
   library-specific exceptions (`SQLAlchemyError`, `RedisError`, ...)
   past their own layer.
2. `register_exception_handlers`, which wires these (plus FastAPI's
   own validation/HTTP exceptions, plus a catch-all) into structured,
   safe JSON responses — never a raw traceback, secret, or internal
   detail reaches the client.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApplicationException(Exception):
    """Base class for all application-raised (as opposed to library-raised)
    exceptions.

    `code` is a short, stable, machine-readable identifier included in
    the API error response; `message` is a client-safe description.
    Neither should ever contain a secret, credential, or connection
    string — see `docs/architecture-decisions.md`, ADR-006.
    """

    code: str = "APPLICATION_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationException(ApplicationException):
    """Raised when required application configuration is missing or invalid."""

    code = "CONFIGURATION_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class DatabaseException(ApplicationException):
    """Raised for PostgreSQL/SQLAlchemy failures the application layer
    chooses to surface as an application-level error rather than letting
    the raw driver exception propagate."""

    code = "DATABASE_ERROR"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class CacheException(ApplicationException):
    """Raised for Redis failures the application layer chooses to surface
    as an application-level error rather than letting the raw client
    exception propagate."""

    code = "CACHE_ERROR"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class ProviderException(ApplicationException):
    """Raised when the external data provider (OKALA) rejects a request or
    otherwise fails in a way that is not retryable. Base class for the more
    specific provider errors below."""

    code = "PROVIDER_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY


class ProviderUnavailableException(ProviderException):
    """Raised when the provider stayed unreachable or kept failing with a
    transient error (timeout, connection failure, HTTP 5xx/429) after every
    permitted retry."""

    code = "PROVIDER_UNAVAILABLE"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class ProviderInvalidResponseException(ProviderException):
    """Raised when the provider answered, but the response was empty,
    not valid JSON, or did not have the expected structure."""

    code = "PROVIDER_INVALID_RESPONSE"
    status_code = status.HTTP_502_BAD_GATEWAY


class ProviderNotFoundException(ProviderException):
    """Raised when the provider reports that a requested resource (for
    example a product) does not exist."""

    code = "PROVIDER_NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


async def _handle_application_exception(request: Request, exc: Exception) -> JSONResponse:
    # FastAPI/Starlette's `add_exception_handler` is typed to accept a
    # handler for the base `Exception`, so each handler below narrows
    # its own `exc` via `assert isinstance(...)` rather than declaring
    # (and having mypy reject) a more specific parameter type.
    assert isinstance(exc, ApplicationException)
    logger.warning("Application exception: %s (%s) on %s", exc.code, exc.message, request.url.path)
    return _error_response(status_code=exc.status_code, code=exc.code, message=exc.message)


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    detail = exc.detail if isinstance(exc.detail, str) else "Request could not be processed."
    return _error_response(status_code=exc.status_code, code="HTTP_ERROR", message=detail)


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # `exc.errors()` from Pydantic is client-safe (field locations and
    # human-readable messages, no server internals), so it is returned
    # as-is rather than collapsed to a generic message.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": exc.errors(),
            }
        },
    )


async def _handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    # Full detail goes to the server-side log only; the client gets a
    # generic, safe message. Never include exc's str() in the response —
    # it can contain internals (e.g. a driver's connection string).
    logger.exception("Unhandled exception on %s", request.url.path)
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="An internal error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register every exception handler on the given FastAPI app.

    Order matters only in that FastAPI dispatches to the most specific
    registered handler first; registering `Exception` last here keeps
    that catch-all from ever shadowing the more specific handlers.
    """

    app.add_exception_handler(ApplicationException, _handle_application_exception)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_exception)
