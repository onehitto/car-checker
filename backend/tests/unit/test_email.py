import pytest

from app.core.config import Settings
from app.modules.notifications.email import (
    ConsoleEmailSender,
    EmailMessage,
    MemoryEmailSender,
    SmtpEmailSender,
    build_email_sender,
    send_safely,
)

MESSAGE = EmailMessage(to="amina@example.com", subject="Hello", body="Body")


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_factory_selects_backend() -> None:
    assert isinstance(build_email_sender(settings(email_backend="memory")), MemoryEmailSender)
    assert isinstance(build_email_sender(settings(email_backend="console")), ConsoleEmailSender)
    smtp = build_email_sender(settings(email_backend="smtp", smtp_host="smtp.example.com"))
    assert isinstance(smtp, SmtpEmailSender)


def test_smtp_requires_host() -> None:
    with pytest.raises(ValueError, match="SMTP_HOST"):
        build_email_sender(settings(email_backend="smtp"))


async def test_memory_sender_keeps_messages() -> None:
    sender = MemoryEmailSender()
    await sender.send(MESSAGE)
    assert sender.outbox == [MESSAGE]


async def test_console_sender_prints_only_outside_production(
    capsys: pytest.CaptureFixture[str],
) -> None:
    await ConsoleEmailSender(show_content=True).send(MESSAGE)
    assert "Subject: Hello" in capsys.readouterr().out

    await ConsoleEmailSender(show_content=False).send(MESSAGE)
    assert "Subject: Hello" not in capsys.readouterr().out


async def test_send_safely_swallows_provider_errors() -> None:
    class FailingSender:
        async def send(self, message: EmailMessage) -> None:
            raise ConnectionError("smtp down")

    assert await send_safely(FailingSender(), MESSAGE, kind="test") is False
    assert await send_safely(MemoryEmailSender(), MESSAGE, kind="test") is True
