from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CourseLevel, CourseModality, CourseStatus
from app.schemas.category import CategoryResponse

PriceField = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class CourseMaterials(BaseModel):
    included: list[str] = Field(default_factory=list)
    required: list[str] = Field(default_factory=list)


# --- Public views ---------------------------------------------------------- #
class CourseListItem(BaseModel):
    """Compact representation for catalog listings (public)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    short_description: str | None = None
    image_url: str | None = None
    modality: CourseModality
    level: CourseLevel
    price: Decimal
    currency: str
    category: CategoryResponse | None = None


class CourseDetailResponse(BaseModel):
    """Full public detail for a course page. Never exposes private links."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    short_description: str | None = None
    description: str | None = None
    objective: str | None = None
    image_url: str | None = None
    modality: CourseModality
    level: CourseLevel
    duration: str | None = None
    price: Decimal
    currency: str
    materials: dict | None = None
    learning_outcomes: list[str] | None = None
    category: CategoryResponse | None = None
    is_published: bool


# --- Admin views ----------------------------------------------------------- #
class CourseAdminResponse(CourseDetailResponse):
    """Admin detail — includes management fields and private links."""

    status: CourseStatus
    whatsapp_group_url: str | None = None
    google_meet_url: str | None = None


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    objective: str | None = None
    image_url: str | None = Field(default=None, max_length=1000)
    modality: CourseModality
    level: CourseLevel
    duration: str | None = Field(default=None, max_length=120)
    price: PriceField
    currency: str = Field(default="COP", min_length=3, max_length=3)
    materials: CourseMaterials | None = None
    learning_outcomes: list[str] | None = None
    status: CourseStatus = CourseStatus.DRAFT
    whatsapp_group_url: str | None = Field(default=None, max_length=1000)
    google_meet_url: str | None = Field(default=None, max_length=1000)
    category_id: uuid.UUID | None = None


class CourseUpdateRequest(BaseModel):
    """All fields optional — PATCH semantics."""

    title: str | None = Field(default=None, min_length=3, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    objective: str | None = None
    image_url: str | None = Field(default=None, max_length=1000)
    modality: CourseModality | None = None
    level: CourseLevel | None = None
    duration: str | None = Field(default=None, max_length=120)
    price: PriceField | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    materials: CourseMaterials | None = None
    learning_outcomes: list[str] | None = None
    status: CourseStatus | None = None
    whatsapp_group_url: str | None = Field(default=None, max_length=1000)
    google_meet_url: str | None = Field(default=None, max_length=1000)
    category_id: uuid.UUID | None = None


class CourseFilterParams(BaseModel):
    """Query params for the public catalog."""

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=12, ge=1, le=100)
    search: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, description="Category slug")
    level: CourseLevel | None = None
    modality: CourseModality | None = None
    sort: str = Field(default="-created_at", description="Field to sort by, prefix - for desc")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit
