"""Scheduler wiring, CLI commands, Redis fail-open and the SMTP sender."""

import smtplib
from typing import Any

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cli import main
from app.core.clock import Clock
from app.core.config import Settings
from app.core.rate_limit import Rate, RedisRateLimiter
from app.jobs.registry import JOBS, JobContext
from app.jobs.scheduler import build_scheduler
from app.modules.notifications.email import EmailMessage, SmtpEmailSender


def settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


async def test_scheduler_registers_every_job() -> None:
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost:1/none")
    ctx = JobContext(session_factory=async_sessionmaker(engine), clock=Clock(), settings=settings())
    scheduler = build_scheduler(ctx, engine)
    jobs = {job.id: job for job in scheduler.get_jobs()}
    assert set(jobs) == set(JOBS)
    assert jobs["generate_alerts"].max_instances == 1
    await engine.dispose()


def test_cli_lists_jobs(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list-jobs"]) == 0
    output = capsys.readouterr().out
    assert "generate_alerts" in output and "dispatch_notifications" in output


def test_cli_rejects_unknown_job(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run-job", "does-not-exist"]) == 2
    assert "Unknown job" in capsys.readouterr().err


async def test_redis_rate_limiter_fails_open() -> None:
    limiter = RedisRateLimiter("redis://127.0.0.1:1/0")
    result = await limiter.hit("login:1.2.3.4", Rate(limit=1, period_seconds=60))
    assert result.allowed
    await limiter.close()


async def test_smtp_sender_uses_starttls_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append(("connect", host, port))

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *_: Any) -> None:
            calls.append(("quit",))

        def starttls(self) -> None:
            calls.append(("starttls",))

        def login(self, username: str, password: str) -> None:
            calls.append(("login", username, password))

        def send_message(self, message: Any) -> None:
            calls.append(("send", message["To"], message["Subject"]))

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    sender = SmtpEmailSender(
        settings(
            email_backend="smtp",
            smtp_host="smtp.example.com",
            smtp_username="mailer",
            smtp_password=SecretStr("s3cret"),
        )
    )
    await sender.send(EmailMessage(to="a@example.com", subject="Hi", body="Body"))
    assert calls == [
        ("connect", "smtp.example.com", 587),
        ("starttls",),
        ("login", "mailer", "s3cret"),
        ("send", "a@example.com", "Hi"),
        ("quit",),
    ]
