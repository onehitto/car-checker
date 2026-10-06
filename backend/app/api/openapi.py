"""Shared OpenAPI documentation fragments."""

from typing import Any

from app.core.responses import ErrorResponse

API_DESCRIPTION = """
Car Checker is a digital vehicle maintenance logbook: maintenance, parts, oil changes, tires,
documents and expirations, mileage, expenses, fuel consumption, alerts and service history.

**Authentication**: send `Authorization: Bearer <access_token>` (obtained from
`/api/v1/auth/login`). Access tokens are short-lived; renew them with `/api/v1/auth/refresh`.

**Envelopes**: successful responses are `{"success": true, "data": ...}` (lists add `meta`
with `page`, `limit`, `total`, `total_pages`). Errors are
`{"success": false, "error": {"code", "message", "fields", "request_id"}}`.

**Units**: distances are stored and returned in kilometres, volumes in litres. Monetary
amounts are decimal strings in the vehicle's currency.
"""

_ERROR_DESCRIPTIONS = {
    400: "Malformed request.",
    401: "Missing, invalid or expired access token.",
    403: "Authenticated, but the vehicle role is insufficient.",
    404: "Resource not found or not accessible.",
    409: "Conflict with the current state (duplicate, resource in use...).",
    413: "Uploaded content too large.",
    415: "Unsupported file type.",
    422: "Validation error; `fields` maps each invalid field to a message.",
    429: "Too many requests; retry after the `Retry-After` delay.",
    503: "Service unavailable.",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Document error responses with the standard error envelope."""
    return {
        code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[code]}
        for code in status_codes
    }


# Default error documentation for authenticated routers.
AUTHENTICATED_ERRORS = error_responses(401, 422, 429)
# Vehicle-scoped routes may additionally fail authorization or lookup.
VEHICLE_ERRORS = error_responses(401, 403, 404, 422, 429)
