from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only record of security/business-relevant events."""

    __tablename__ = "audit_logs"

    # Actor (nullable for system/anonymous events). No FK so logs survive deletes.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Non-sensitive contextual metadata only.
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
