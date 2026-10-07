"""Scheduled jobs."""

from datetime import timedelta

from sqlalchemy import delete, exists, or_, select, update

from app.jobs.registry import JobContext, JobResult, job
from app.modules.alerts.engine import sync_all_vehicles
from app.modules.attachments.models import Attachment, AttachmentEntity
from app.modules.attachments.service import ENTITY_MODELS, delete_stored_files
from app.modules.attachments.storage import build_storage
from app.modules.auth.models import PasswordResetToken, RefreshToken, UserSession
from app.modules.notes.models import Note, NoteEntity
from app.modules.notifications.dispatcher import build_providers, dispatch_pending
from app.modules.notifications.email import build_email_sender

SESSION_RETENTION = timedelta(days=30)
RESET_TOKEN_RETENTION = timedelta(days=1)
# Files younger than this may belong to an upload whose transaction is still running.
ORPHAN_FILE_GRACE = timedelta(hours=1)


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
    "dispatch_notifications",
    description="Send pending e-mail/push/SMS notifications of new alerts.",
    trigger="interval",
    minutes=1,
)
async def dispatch_notifications(ctx: JobContext) -> JobResult:
    sender = ctx.extras.get("email_sender") or build_email_sender(ctx.settings)
    providers = build_providers(sender, ctx.settings)
    result = await dispatch_pending(ctx.session_factory, providers, ctx.clock)
    return result.counts


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


@job(
    "cleanup_orphan_files",
    description=(
        "Delete attachments of deleted records and stored files without metadata; "
        "keep notes of deleted records as vehicle notes."
    ),
    trigger="cron",
    hour=4,
    minute=0,
)
async def cleanup_orphan_files(ctx: JobContext) -> JobResult:
    storage = ctx.extras.get("storage") or build_storage(ctx.settings)
    async with ctx.session_factory() as session:
        # 1. Attachments whose parent record was deleted (polymorphic: no foreign key).
        orphan_keys: list[str] = []
        for entity_type, model in ENTITY_MODELS.items():
            result = await session.scalars(
                delete(Attachment)
                .where(
                    Attachment.entity_type == entity_type,
                    ~exists(select(model.id).where(model.id == Attachment.entity_id)),
                )
                .returning(Attachment.storage_key)
            )
            orphan_keys.extend(result)
        # Notes about a deleted record keep their content as vehicle-level notes.
        detached = 0
        for note_entity in NoteEntity:
            model = ENTITY_MODELS[AttachmentEntity(note_entity.value)]
            updated = await session.execute(
                update(Note)
                .where(
                    Note.entity_type == note_entity,
                    ~exists(select(model.id).where(model.id == Note.entity_id)),
                )
                .values(entity_type=None, entity_id=None)
            )
            detached += updated.rowcount  # type: ignore[attr-defined]
        await session.commit()
        known = set(await session.scalars(select(Attachment.storage_key)))
    await delete_stored_files(storage, orphan_keys)

    # 2. Stored files without a metadata row (deleted vehicles/accounts, failed uploads).
    stray = [
        key
        async for key in storage.list_keys(ctx.clock.now() - ORPHAN_FILE_GRACE)
        if key not in known
    ]
    await delete_stored_files(storage, stray)
    return {
        "orphan_attachments": len(orphan_keys),
        "stray_files": len(stray),
        "detached_notes": detached,
    }
