import pytest
from sqlalchemy import column, select, table
from sqlalchemy.dialects import postgresql

from app.core.exceptions import ValidationAppError
from app.core.pagination import Page, PageParams, apply_sort, like_pattern

items = table("items", column("id"), column("name"), column("price"))
ALLOWED = {"name": items.c.name, "price": items.c.price}


def compile_sql(stmt: object) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]


def test_page_params_offset() -> None:
    assert PageParams(page=3, limit=20).offset == 40


@pytest.mark.parametrize(("total", "pages"), [(0, 0), (1, 1), (20, 1), (21, 2), (150, 8)])
def test_page_meta_total_pages(total: int, pages: int) -> None:
    page = Page(items=[], total=total, params=PageParams(page=1, limit=20))
    assert page.meta == {"page": 1, "limit": 20, "total": total, "total_pages": pages}


def test_page_map_transforms_items() -> None:
    page = Page(items=[1, 2], total=2, params=PageParams()).map(str)
    assert page.items == ["1", "2"]


def test_apply_sort_uses_whitelist_and_direction() -> None:
    stmt = apply_sort(select(items), "-price,name", ALLOWED, default="name", tiebreaker=items.c.id)
    assert "ORDER BY items.price DESC NULLS LAST, items.name ASC NULLS LAST, items.id DESC" in (
        compile_sql(stmt)
    )


def test_apply_sort_falls_back_to_default() -> None:
    assert "ORDER BY items.name DESC" in compile_sql(
        apply_sort(select(items), None, ALLOWED, "-name")
    )


def test_apply_sort_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationAppError) as exc_info:
        apply_sort(select(items), "password", ALLOWED, default="name")
    assert exc_info.value.fields is not None
    assert "Unknown sort field 'password'" in exc_info.value.fields["sort"]


def test_like_pattern_escapes_wildcards() -> None:
    assert like_pattern("50%_off\\") == "%50\\%\\_off\\\\%"
