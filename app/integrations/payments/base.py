"""Payment provider abstraction.

Business logic depends only on this interface, never on a concrete provider.
Swapping providers (Wompi -> another) requires only a new implementation of
``PaymentProvider`` plus a factory entry — no changes to services.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.models.enums import PaymentStatus


@dataclass(slots=True)
class PaymentIntent:
    """Everything the provider needs to create a payment."""

    reference: str
    amount: Decimal
    currency: str
    description: str
    customer_email: str
    customer_name: str | None = None


@dataclass(slots=True)
class PaymentCreation:
    """Result of creating a payment: where to send the user and how to track it."""

    reference: str
    checkout_url: str | None
    external_transaction_id: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WebhookEvent:
    """Normalized representation of a provider webhook event."""

    event_id: str  # stable unique id used for idempotency
    reference: str | None
    external_transaction_id: str | None
    status: PaymentStatus
    amount: Decimal | None
    currency: str | None
    raw: dict[str, Any] = field(default_factory=dict)


class InvalidWebhookError(Exception):
    """Raised when a webhook cannot be authenticated or parsed."""


class PaymentProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def create_payment(self, intent: PaymentIntent) -> PaymentCreation:
        """Create a payment/checkout session with the provider."""

    @abc.abstractmethod
    def verify_and_parse_webhook(
        self, *, raw_body: bytes, headers: dict[str, str]
    ) -> WebhookEvent:
        """Authenticate a webhook and return a normalized event.

        Raises ``InvalidWebhookError`` if the signature is invalid or the
        payload is not recognized. This MUST reject spoofed requests.
        """

    @abc.abstractmethod
    async def verify_payment(self, external_transaction_id: str) -> PaymentStatus:
        """Query the provider for the current status of a transaction."""

    async def refund_payment(
        self, external_transaction_id: str, amount: Decimal | None = None
    ) -> bool:
        """Refund a transaction. Optional — default raises NotImplemented."""
        raise NotImplementedError("Refunds are not implemented for this provider.")
