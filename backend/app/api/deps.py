"""Common FastAPI dependencies."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, get_clock
from app.core.config import Settings
from app.db.session import Database


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request. Services commit explicitly; uncommitted work is rolled back."""
    database: Database = request.app.state.db
    async with database.session_factory() as session:
        yield session


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
ClockDep = Annotated[Clock, Depends(get_clock)]
