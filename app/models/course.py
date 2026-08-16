from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CourseLevel, CourseModality, CourseStatus

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.enrollment import Enrollment
    from app.models.purchase import Purchase


class Course(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        Index("ix_courses_status", "status"),
        Index("ix_courses_category_id", "category_id"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    modality: Mapped[CourseModality] = mapped_column(
        Enum(CourseModality, native_enum=False, length=20), nullable=False
    )
    level: Mapped[CourseLevel] = mapped_column(
        Enum(CourseLevel, native_enum=False, length=20), nullable=False
    )
    duration: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Money: stored as Decimal, NEVER float. Currency stored explicitly.
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    # Structured materials, e.g. {"included": [...], "required": [...]}.
    materials: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    learning_outcomes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, native_enum=False, length=20),
        default=CourseStatus.DRAFT,
        nullable=False,
    )

    # --- Private links (only exposed to authorized, enrolled users) ---
    whatsapp_group_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    google_meet_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[Category | None] = relationship(back_populates="courses")

    purchases: Mapped[list[Purchase]] = relationship(back_populates="course")
    enrollments: Mapped[list[Enrollment]] = relationship(back_populates="course")

    @property
    def is_published(self) -> bool:
        return self.status == CourseStatus.PUBLISHED
