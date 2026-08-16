"""Email provider abstraction.

Business code depends on ``EmailProvider`` only, so SMTP can later be swapped
for SendGrid/Resend/SES without touching services.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(slots=True)
class EmailMessage:
    to: str
    subject: str
    html_body: str
    text_body: str | None = None


class EmailProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def send(self, message: EmailMessage) -> None:
        """Send an email. Raises on failure so the caller can retry/record."""
