"""Global exception handlers producing the standard error envelope."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

HTTP_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "AUTHENTICATION_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}

# Location prefixes that only describe where FastAPI found the value.
_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie", "form"}


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    fields: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    error["request_id"] = get_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": error},
        headers=headers,
    )


def format_validation_errors(errors: list[Any]) -> dict[str, str]:
    """Flatten Pydantic errors into {"dotted.path": "message"} (first message per field)."""
    fields: dict[str, str] = {}
    for error in errors:
        location = [str(part) for part in error.get("loc", ())]
        if location and location[0] in _LOCATION_PREFIXES:
            location = location[1:]
        key = ".".join(location) or "__root__"
        message = str(error.get("msg", "Invalid value."))
        message = message.removeprefix("Value error, ")
        fields.setdefault(key, message)
    return fields


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - registered for AppError only
    if exc.status_code >= 500:
        logger.error("app_error", code=exc.error_code, message=exc.message)
    return error_response(
        request, exc.status_code, exc.error_code, exc.message, exc.fields, exc.headers
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    fields = format_validation_errors(jsonable_encoder(exc.errors()))
    return error_response(
        request, 422, "VALIDATION_ERROR", "The request contains invalid fields.", fields
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be processed."
    if exc.status_code == 404 and message == "Not Found":
        message = "The requested resource was not found."
    return error_response(
        request, exc.status_code, code, message, headers=getattr(exc, "headers", None)
    )


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Unique/foreign-key races that escaped service-level checks. Never leak SQL details.
    logger.warning("integrity_error", error_type=type(exc).__name__)
    return error_response(
        request, 409, "CONFLICT", "The request conflicts with the current state of the resource."
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=request.url.path, method=request.method)
    return error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
