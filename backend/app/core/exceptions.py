"""Application error hierarchy.

Services raise these exceptions; they never build HTTP responses themselves. Global handlers
(`app.core.error_handlers`) convert them into the standard error envelope.
"""

from typing import ClassVar


class AppError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "BAD_REQUEST"
    default_message: ClassVar[str] = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.error_code = code or self.code
        self.fields = fields
        self.headers = headers
        super().__init__(self.message)


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"
    default_message = "Authentication is required to access this resource."

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        super().__init__(message, code=code, headers={"WWW-Authenticate": "Bearer"})


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"
    default_message = "Invalid email or password."


class InvalidTokenError(AuthenticationError):
    code = "INVALID_TOKEN"
    default_message = "The token is invalid or has expired."


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    default_message = "The requested resource was not found."

    def __init__(self, resource: str | None = None, message: str | None = None) -> None:
        super().__init__(message or (f"{resource} not found." if resource else None))


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    default_message = "The request conflicts with the current state of the resource."


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"
    default_message = "The uploaded content is too large."


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"
    default_message = "This file type is not supported."


class ValidationAppError(AppError):
    """Field-level validation failure detected by a service (same shape as schema errors)."""

    status_code = 422
    code = "VALIDATION_ERROR"
    default_message = "The request contains invalid fields."


class BusinessRuleError(AppError):
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"
    default_message = "The request violates a business rule."


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    default_message = "Too many requests. Please retry later."

    def __init__(self, retry_after: int) -> None:
        super().__init__(headers={"Retry-After": str(retry_after)})


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    default_message = "The service is temporarily unavailable."
