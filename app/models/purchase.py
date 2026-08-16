from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PurchaseStatus

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.payment import Payment
    from app.models.user import User


class Purchase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchases"
    __table_args__ = (
        Index("ix_purchases_user_id", "user_id"),
        Index("ix_purchases_course_id", "course_id"),
        Index("ix_purchases_status", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )

    # Price is captured AT PURCHASE TIME and never re-derived from the course.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, native_enum=False, length=20),
        default=PurchaseStatus.PENDING,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="purchases")
    course: Mapped[Course] = relationship(back_populates="purchases")
    payment: Mapped[Payment | None] = relationship(
        back_populates="purchase", uselist=False, cascade="all, delete-orphan"
    )
    enrollment: Mapped[Enrollment | None] = relationship(
        back_populates="purchase", uselist=False
    )
