"""Email delivery abstraction.

* `console` — development: prints messages to stdout (never through the logger, never in
  production, where content is withheld).
* `smtp`    — any SMTP provider (STARTTLS + authentication).
* `memory`  — tests: keeps messages in `outbox`.
"""

import asyncio
import smtplib
import sys
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from typing import Protocol

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SMTP_TIMEOUT_SECONDS = 15


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailSender:
    def __init__(self, *, show_content: bool) -> None:
        self.show_content = show_content

    async def send(self, message: EmailMessage) -> None:
        if not self.show_content:
            logger.warning("email_not_delivered", reason="console backend in production")
            return
        sys.stdout.write(
            f"\n----- email -----\nTo: {message.to}\nSubject: {message.subject}\n\n"
            f"{message.body}\n-----------------\n"
        )
        sys.stdout.flush()


class MemoryEmailSender:
    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        if not settings.smtp_host:
            raise ValueError("SMTP_HOST is required when EMAIL_BACKEND=smtp")
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.starttls = settings.smtp_starttls
        self.sender = settings.email_from

    def _send_sync(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self.sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as client:
            if self.starttls:
                client.starttls()
            if self.username and self.password:
                client.login(self.username, self.password.get_secret_value())
            client.send_message(mime)

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_sync, message)


def build_email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend == "smtp":
        return SmtpEmailSender(settings)
    if settings.email_backend == "memory":
        return MemoryEmailSender()
    return ConsoleEmailSender(show_content=not settings.is_production)


async def send_safely(sender: EmailSender, message: EmailMessage, *, kind: str) -> bool:
    """Send without propagating provider errors (used from background tasks)."""
    try:
        await sender.send(message)
    except Exception as exc:  # noqa: BLE001 - delivery failures must not crash the caller
        logger.error("email_delivery_failed", kind=kind, error=type(exc).__name__)
        return False
    return True
