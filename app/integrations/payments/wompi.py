"""Wompi payment provider (Colombia).

Uses Wompi's hosted Checkout (redirect) flow:
  * ``create_payment`` builds a signed checkout URL (integrity signature).
  * The definitive status arrives via a webhook whose ``signature.checksum``
    is validated against the events secret — the frontend is NEVER trusted to
    confirm a payment.
  * ``verify_payment`` polls the transactions API as a fallback.

Amounts are handled in COP cents (integers) as Wompi requires, converting
to/from ``Decimal`` at the boundary. Money never uses float internally.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.integrations.payments.base import (
    InvalidWebhookError,
    PaymentCreation,
    PaymentIntent,
    PaymentProvider,
    WebhookEvent,
)
from app.models.enums import PaymentStatus

_WOMPI_STATUS_MAP: dict[str, PaymentStatus] = {
    "APPROVED": PaymentStatus.APPROVED,
    "DECLINED": PaymentStatus.DECLINED,
    "VOIDED": PaymentStatus.VOIDED,
    "ERROR": PaymentStatus.ERROR,
    "PENDING": PaymentStatus.PENDING,
}


def _to_cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def _from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def _dig(data: dict[str, Any], dotted_path: str) -> Any:
    node: Any = data
    for part in dotted_path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


class WompiPaymentProvider(PaymentProvider):
    name = "wompi"

    def __init__(self) -> None:
        self._public_key = settings.payment_public_key
        self._private_key = settings.payment_api_key
        self._integrity_secret = settings.payment_integrity_secret
        self._events_secret = settings.payment_webhook_secret
        self._checkout_url = settings.payment_checkout_url
        self._base_url = settings.payment_base_url
        self._redirect_url = settings.payment_redirect_url

    # ------------------------------------------------------------------ #
    async def create_payment(self, intent: PaymentIntent) -> PaymentCreation:
        amount_in_cents = _to_cents(intent.amount)
        signature = hashlib.sha256(
            f"{intent.reference}{amount_in_cents}{intent.currency}"
            f"{self._integrity_secret}".encode()
        ).hexdigest()

        params = {
            "public-key": self._public_key,
            "currency": intent.currency,
            "amount-in-cents": str(amount_in_cents),
            "reference": intent.reference,
            "signature:integrity": signature,
            "redirect-url": self._redirect_url,
            "customer-data:email": intent.customer_email,
        }
        if intent.customer_name:
            params["customer-data:full-name"] = intent.customer_name

        checkout_url = f"{self._checkout_url}?{urlencode(params)}"
        return PaymentCreation(
            reference=intent.reference,
            checkout_url=checkout_url,
            status=PaymentStatus.PENDING,
            raw={"amount_in_cents": amount_in_cents},
        )

    # ------------------------------------------------------------------ #
    def verify_and_parse_webhook(
        self, *, raw_body: bytes, headers: dict[str, str]
    ) -> WebhookEvent:
        import json

        try:
            payload: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidWebhookError("Malformed webhook body") from exc

        signature = payload.get("signature") or {}
        properties: list[str] = signature.get("properties") or []
        checksum: str | None = signature.get("checksum")
        timestamp = payload.get("timestamp")
        data = payload.get("data") or {}

        if not checksum or not properties:
            raise InvalidWebhookError("Missing signature in webhook")

        # Rebuild the checksum: concat of property values + timestamp + secret.
        concatenated = "".join(str(_dig(data, prop) or "") for prop in properties)
        concatenated += str(timestamp or "")
        concatenated += self._events_secret
        expected = hashlib.sha256(concatenated.encode()).hexdigest()

        if not _secure_equals(expected, checksum):
            raise InvalidWebhookError("Webhook signature mismatch")

        transaction = data.get("transaction") or {}
        tx_id = transaction.get("id")
        status_raw = transaction.get("status", "")
        status = _WOMPI_STATUS_MAP.get(status_raw, PaymentStatus.PENDING)
        amount_cents = transaction.get("amount_in_cents")

        if not tx_id:
            raise InvalidWebhookError("Webhook missing transaction id")

        return WebhookEvent(
            # Wompi has no dedicated event id; (tx, status) is stable & unique.
            event_id=f"{tx_id}:{status_raw}",
            reference=transaction.get("reference"),
            external_transaction_id=str(tx_id),
            status=status,
            amount=_from_cents(amount_cents) if amount_cents is not None else None,
            currency=transaction.get("currency"),
            raw=transaction,
        )

    # ------------------------------------------------------------------ #
    async def verify_payment(self, external_transaction_id: str) -> PaymentStatus:
        url = f"{self._base_url}/transactions/{external_transaction_id}"
        headers = {"Authorization": f"Bearer {self._private_key}"}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json().get("data") or {}
        return _WOMPI_STATUS_MAP.get(data.get("status", ""), PaymentStatus.PENDING)


def _secure_equals(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a.lower(), b.lower())
