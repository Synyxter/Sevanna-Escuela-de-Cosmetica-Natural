from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import PaymentStatus


class PaymentCreateRequest(BaseModel):
    purchase_id: uuid.UUID


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_id: uuid.UUID
    provider: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    external_reference: str
    checkout_url: str | None = None
    created_at: datetime


class PaymentInitResponse(BaseModel):
    """Returned to the frontend to redirect the user to the provider."""

    payment_id: uuid.UUID
    checkout_url: str | None
    reference: str
    status: PaymentStatus


class WebhookResponse(BaseModel):
    received: bool = True
    processed: bool
    detail: str | None = None


# Webhook payloads are provider-specific and validated inside the integration,
# so the endpoint accepts a raw JSON body.
WebhookPayload = dict[str, Any]
