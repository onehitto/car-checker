"""Reusable pagination, sorting and search helpers for list endpoints."""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query
from sqlalchemy import ColumnElement, Select, SQLColumnExpression, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute

from app.core.exceptions import ValidationAppError

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

SortQuery = Annotated[
    str | None,
    Query(
        max_length=200,
        pattern=r"^[a-z0-9_,+\-]*$",
        description="Comma-separated sort fields; prefix a field with '-' for descending order.",
    ),
]
SearchQuery = Annotated[
    str | None, Query(min_length=1, max_length=100, description="Case-insensitive search text.")
]


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int = 1
    limit: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def get_page_params(
    page: Annotated[int, Query(ge=1, le=1_000_000, description="Page number (1-based)")] = 1,
    limit: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page (max 100)")
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, limit=limit)


PageDep = Annotated[PageParams, Depends(get_page_params)]


@dataclass(slots=True)
class Page[T]:
    items: list[T]
    total: int
    params: PageParams

    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.params.limit) if self.total else 0

    @property
    def meta(self) -> dict[str, int]:
        return {
            "page": self.params.page,
            "limit": self.params.limit,
            "total": self.total,
            "total_pages": self.total_pages,
        }

    def map[U](self, transform: Callable[[T], U]) -> "Page[U]":
        return Page([transform(item) for item in self.items], self.total, self.params)


async def count_rows(session: AsyncSession, stmt: Select[Any]) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return int(await session.scalar(count_stmt) or 0)


async def paginate[T](session: AsyncSession, stmt: Select[T], params: PageParams) -> Page[T]:
    """Paginate a statement selecting one entity/column."""
    total = await count_rows(session, stmt)
    result = await session.scalars(stmt.limit(params.limit).offset(params.offset))
    return Page(list(result.all()), total, params)


async def paginate_rows(session: AsyncSession, stmt: Select[Any], params: PageParams) -> Page[Any]:
    """Paginate a statement selecting several columns (returns Row objects)."""
    total = await count_rows(session, stmt)
    result = await session.execute(stmt.limit(params.limit).offset(params.offset))
    return Page(list(result.all()), total, params)


def paginated(page: Page[Any]) -> dict[str, Any]:
    """Wrap a page in the list envelope."""
    return {"success": True, "data": page.items, "meta": page.meta}


SortColumn = ColumnElement[Any] | SQLColumnExpression[Any] | QueryableAttribute[Any]


def apply_sort[S: Select[Any]](
    stmt: S,
    sort: str | None,
    allowed: Mapping[str, SortColumn],
    default: str,
    tiebreaker: SortColumn | None = None,
) -> S:
    """Apply `sort=field,-other` ordering restricted to whitelisted fields."""
    clauses: list[ColumnElement[Any]] = []
    for raw in (sort or default).split(","):
        token = raw.strip()
        if not token:
            continue
        descending = token.startswith("-")
        name = token.lstrip("-+")
        column = allowed.get(name)
        if column is None:
            raise ValidationAppError(
                fields={"sort": f"Unknown sort field '{name}'. Allowed: {', '.join(allowed)}."}
            )
        clauses.append(column.desc().nulls_last() if descending else column.asc().nulls_last())
    if tiebreaker is not None:
        clauses.append(tiebreaker.desc())
    return stmt.order_by(*clauses)


def like_pattern(term: str) -> str:
    """Build a `%term%` pattern with LIKE wildcards escaped (use with `escape='\\\\'`)."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
