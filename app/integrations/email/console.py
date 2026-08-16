"""Console email provider — logs emails instead of sending (development)."""

from __future__ import annotations

import logging

from app.integrations.email.base import EmailMessage, EmailProvider

logger = logging.getLogger("sevanna")


class ConsoleEmailProvider(EmailProvider):
    name = "console"

    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "email (console)",
            extra={
                "event": "email_console",
                "to": message.to,
                "subject": message.subject,
            },
        )
        # Print a readable preview to stdout for local development.
        print(  # noqa: T201 - intentional dev output
            f"\n--- EMAIL (console provider) ---\n"
            f"To: {message.to}\nSubject: {message.subject}\n\n"
            f"{message.text_body or message.html_body}\n"
            f"--- end email ---\n"
        )
