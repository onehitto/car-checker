"""Standard response envelopes shared by every endpoint.

Success:   {"success": true, "data": ...}
List:      {"success": true, "data": [...], "meta": {"page", "limit", "total", "total_pages"}}
Error:     {"success": false, "error": {"code", "message", "fields", "request_id"}}
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiResponse[DataT](BaseModel):
    success: Literal[True] = True
    data: DataT


class PageMeta(BaseModel):
    page: int = Field(ge=1, examples=[1])
    limit: int = Field(ge=1, examples=[20])
    total: int = Field(ge=0, examples=[150])
    total_pages: int = Field(ge=0, examples=[8])


class PaginatedResponse[ItemT](BaseModel):
    success: Literal[True] = True
    data: list[ItemT]
    meta: PageMeta


class ErrorDetail(BaseModel):
    code: str = Field(examples=["VALIDATION_ERROR"])
    message: str = Field(examples=["The request contains invalid fields."])
    fields: dict[str, str] | None = Field(
        default=None, examples=[{"mileage": "Input should be greater than or equal to 0"}]
    )
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorDetail


def success(data: Any) -> dict[str, Any]:
    """Wrap a payload in the success envelope (validated by the route's response_model)."""
    return {"success": True, "data": data}
