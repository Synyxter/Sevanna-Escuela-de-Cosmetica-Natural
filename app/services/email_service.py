"""Email sending with delivery tracking and retries.

Design guarantees:
- Sending email NEVER determines the state of a payment/purchase. Failures are
  recorded (EmailLog -> FAILED) but do not raise into business flows.
- Each send is retried a few times with the outcome persisted so failed emails
  can be inspected/re-sent later.
- Runs off the request path via FastAPI BackgroundTasks (see api/deps + routers).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.integrations.email.base import EmailMessage
from app.integrations.email.factory import get_email_provider
from app.models.email_log import EmailLog
from app.models.enums import EmailStatus

logger = logging.getLogger("sevanna")

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (1, 3, 5)


class EmailService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.provider = get_email_provider()

    async def send(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        template: str | None = None,
        related_entity_id: uuid.UUID | None = None,
    ) -> EmailLog:
        log = EmailLog(
            to_email=to,
            subject=subject,
            template=template,
            status=EmailStatus.PENDING,
            attempts=0,
            related_entity_id=related_entity_id,
        )
        self.session.add(log)
        await self.session.flush()

        message = EmailMessage(to=to, subject=subject, html_body=html_body, text_body=text_body)

        last_error: str | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            log.attempts = attempt
            try:
                await self.provider.send(message)
                log.status = EmailStatus.SENT
                log.sent_at = datetime.now(UTC)
                log.last_error = None
                await self.session.commit()
                logger.info(
                    "email sent", extra={"event": "email_sent", "to": to}
                )
                return log
            except Exception as exc:  # noqa: BLE001 - record and retry any failure
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "email send failed (attempt %s/%s): %s",
                    attempt,
                    MAX_ATTEMPTS,
                    last_error,
                    extra={"event": "email_failed", "to": to},
                )
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS[attempt - 1])

        log.status = EmailStatus.FAILED
        log.last_error = last_error
        await self.session.commit()
        return log


# --------------------------------------------------------------------------- #
# Background-task entrypoints — open their own session so they run independently
# of the originating request/transaction.
# --------------------------------------------------------------------------- #
async def send_email_background(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    template: str | None = None,
    related_entity_id: uuid.UUID | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        service = EmailService(session)
        try:
            await service.send(
                to=to,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                template=template,
                related_entity_id=related_entity_id,
            )
        except Exception:  # noqa: BLE001 - never let email break the caller
            logger.exception("Unexpected error in background email task")
