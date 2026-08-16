"""Shared response envelopes and pagination schemas.

Every endpoint returns a consistent envelope:
  success -> {"success": true, "data": ..., "message": ...}
  error   -> {"success": false, "error": {"code": ..., "message": ...}}
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "Operación realizada correctamente"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str | None = None


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


class MessageResponse(BaseModel):
    success: bool = True
    message: str


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=12, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def build_page(items: list[T], *, total: int, page: int, limit: int) -> Page[T]:
    total_pages = (total + limit - 1) // limit if limit else 0
    return Page(
        items=items,
        pagination=PaginationMeta(
            page=page, limit=limit, total=total, total_pages=total_pages
        ),
    )
