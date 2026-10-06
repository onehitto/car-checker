"""Import every ORM model so that `Base.metadata` is complete (Alembic autogenerate, tests)."""

from app.db.base import Base

__all__ = ["Base"]
