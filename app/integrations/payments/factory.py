"""Factory + cached selector for the configured payment provider."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.integrations.payments.base import PaymentProvider
from app.integrations.payments.fake import FakePaymentProvider
from app.integrations.payments.wompi import WompiPaymentProvider


@lru_cache
def get_payment_provider() -> PaymentProvider:
    match settings.payment_provider:
        case "wompi":
            return WompiPaymentProvider()
        case "fake":
            return FakePaymentProvider()
        case _:  # pragma: no cover - guarded by config typing
            raise ValueError(f"Unknown payment provider: {settings.payment_provider}")
