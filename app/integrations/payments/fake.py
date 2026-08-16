"""In-memory fake payment provider for local development and tests.

- ``create_payment`` returns a fake checkout URL and a deterministic
  transaction id derived from the reference.
- Webhooks are "authenticated" by a shared static token in the
  ``X-Fake-Signature`` header (matching the configured webhook secret), so the
  same idempotency/validation code paths are exercised in tests.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.integrations.payments.base import (
    InvalidWebhookError,
    PaymentCreation,
    PaymentIntent,
    PaymentProvider,
    WebhookEvent,
)
from app.models.enums import PaymentStatus

_STATUS_MAP = {s.value: s for s in PaymentStatus}


def _fake_tx_id(reference: str) -> str:
    return "fake-" + hashlib.sha256(reference.encode()).hexdigest()[:24]


class FakePaymentProvider(PaymentProvider):
    name = "fake"

    async def create_payment(self, intent: PaymentIntent) -> PaymentCreation:
        tx_id = _fake_tx_id(intent.reference)
        return PaymentCreation(
            reference=intent.reference,
            checkout_url=f"https://fake-checkout.local/pay/{intent.reference}",
            external_transaction_id=tx_id,
            status=PaymentStatus.PENDING,
            raw={"fake": True, "amount": str(intent.amount)},
        )

    def verify_and_parse_webhook(
        self, *, raw_body: bytes, headers: dict[str, str]
    ) -> WebhookEvent:
        provided = headers.get("x-fake-signature") or headers.get("X-Fake-Signature")
        if provided != (settings.payment_webhook_secret or "fake-secret"):
            raise InvalidWebhookError("Invalid fake signature")

        try:
            payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidWebhookError("Malformed body") from exc

        reference = payload.get("reference")
        status_raw = str(payload.get("status", "APPROVED"))
        status = _STATUS_MAP.get(status_raw, PaymentStatus.PENDING)
        tx_id = payload.get("transaction_id") or (_fake_tx_id(reference) if reference else None)
        amount = payload.get("amount")

        if not tx_id:
            raise InvalidWebhookError("Missing transaction reference")

        return WebhookEvent(
            event_id=f"{tx_id}:{status_raw}",
            reference=reference,
            external_transaction_id=str(tx_id),
            status=status,
            amount=Decimal(str(amount)) if amount is not None else None,
            currency=payload.get("currency", settings.payment_currency),
            raw=payload,
        )

    async def verify_payment(self, external_transaction_id: str) -> PaymentStatus:
        return PaymentStatus.APPROVED
