"""Structured logging (structlog) with automatic redaction of sensitive values.

Every log line is a structured event. Context such as `request_id` and `user_id` is bound
through `structlog.contextvars` by the middleware and the authentication dependency, so it
appears on every line emitted while handling a request.
"""

import logging
import sys
from collections.abc import Mapping
from typing import Any

import structlog
from structlog.types import EventDict, Processor, WrappedLogger

from app.core.config import Settings

REDACTED = "[REDACTED]"

# A key is considered sensitive when it contains one of these fragments (case-insensitive).
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "token",
    "secret",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "email",
    "phone",
)


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: REDACTED if isinstance(key, str) and _is_sensitive(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return type(value)(_redact(item) for item in value)
    return value


def redact_sensitive_values(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """structlog processor replacing values of sensitive keys, recursively."""
    return {
        key: REDACTED if key != "event" and _is_sensitive(key) else _redact(value)
        for key, value in event_dict.items()
    }


def configure_logging(settings: Settings) -> None:
    """Route stdlib and structlog records through one structured pipeline."""
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_sensitive_values,
        structlog.processors.StackInfoRenderer(),
    ]
    renderer: Processor
    if settings.log_format == "json":
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    # Uvicorn's own access log duplicates our access log middleware (and logs query strings).
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error", "apscheduler"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name)  # type: ignore[no-any-return]
