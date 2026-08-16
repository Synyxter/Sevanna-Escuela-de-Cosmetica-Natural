"""Factory + cached selector for the configured email provider."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.integrations.email.base import EmailProvider
from app.integrations.email.console import ConsoleEmailProvider
from app.integrations.email.smtp import SMTPEmailProvider


@lru_cache
def get_email_provider() -> EmailProvider:
    match settings.email_provider:
        case "smtp":
            return SMTPEmailProvider()
        case "console":
            return ConsoleEmailProvider()
        case _:  # pragma: no cover
            raise ValueError(f"Unknown email provider: {settings.email_provider}")
