from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus

if TYPE_CHECKING:
    from app.models.purchase import Purchase


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"

    purchase_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False)

    # Provider's transaction id — unique so the same transaction is never
    # recorded twice (supports webhook idempotency).
    external_transaction_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    # Reference we send to the provider to correlate the payment back to us.
    external_reference: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=20),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    checkout_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Raw provider payload (sanitized) for auditing/debugging.
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    purchase: Mapped[Purchase] = relationship(back_populates="payment")
