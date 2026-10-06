"""Scheduled jobs."""

from datetime import timedelta

from sqlalchemy import delete, or_

from app.jobs.registry import JobContext, JobResult, job
from app.modules.alerts.engine import sync_all_vehicles
from app.modules.auth.models import PasswordResetToken, RefreshToken, UserSession

SESSION_RETENTION = timedelta(days=30)
RESET_TOKEN_RETENTION = timedelta(days=1)


@job(
    "generate_alerts",
    description="Refresh maintenance, document, part and mileage alerts of every vehicle.",
    trigger="interval",
    hours=1,
)
async def generate_alerts(ctx: JobContext) -> JobResult:
    result = await sync_all_vehicles(ctx.session_factory, ctx.clock)
    return {"created": len(result.created), "resolved": result.resolved}


@job(
    "cleanup_expired_tokens",
    description="Delete expired refresh/reset tokens and old revoked or expired sessions.",
    trigger="cron",
    hour=3,
    minute=0,
)
async def cleanup_expired_tokens(ctx: JobContext) -> JobResult:
    now = ctx.clock.now()
    async with ctx.session_factory() as session:
        # Used (rotated) refresh tokens are kept until they expire: re-use detection needs them.
        tokens = await session.execute(delete(RefreshToken).where(RefreshToken.expires_at < now))
        resets = await session.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.expires_at < now - RESET_TOKEN_RETENTION
            )
        )
        sessions = await session.execute(
            delete(UserSession).where(
                or_(
                    UserSession.revoked_at < now - SESSION_RETENTION,
                    UserSession.expires_at < now - SESSION_RETENTION,
                )
            )
        )
        await session.commit()
    return {
        "refresh_tokens": tokens.rowcount,  # type: ignore[attr-defined]
        "reset_tokens": resets.rowcount,  # type: ignore[attr-defined]
        "sessions": sessions.rowcount,  # type: ignore[attr-defined]
    }
