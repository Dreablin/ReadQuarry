"""Global FastAPI exception handlers: user-friendly JSON and safe 500 responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _detail_to_message(detail: Any) -> str:
    """Normalize HTTPException detail to a single user-facing string."""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc", ())
                msg = item.get("msg", "")
                parts.append(f"{'/'.join(str(x) for x in loc)}: {msg}")
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else "Invalid request"
    return str(detail)


async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Return consistent JSON for HTTP errors."""
    message = _detail_to_message(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": message})


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a readable validation summary plus structured errors for clients."""
    errors = exc.errors()
    parts = []
    for err in errors[:12]:
        loc = err.get("loc", ())
        msg = err.get("msg", "")
        loc_s = "/".join(str(x) for x in loc if x != "body")
        parts.append(f"{loc_s}: {msg}" if loc_s else msg)
    summary = "; ".join(parts) if parts else "The request could not be validated."
    return JSONResponse(
        status_code=422,
        content={"detail": summary, "errors": jsonable_encoder(errors)},
    )


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Log server errors and avoid leaking internal details to clients."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
