"""Payment service — provider orchestration and webhook processing.

Guarantees:
- The definitive payment state comes from the provider webhook, never the
  frontend (Rule 5/6).
- Webhook processing is idempotent: a duplicated event does not create a second
  purchase, enrollment, or email (Rule 7/34).
- Payment confirmation -> purchase PAID -> enrollment ACTIVE runs inside a single
  DB transaction with a row lock on the purchase to survive concurrent webhooks
  (Rule 57/58). If anything fails, the whole thing rolls back.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.integrations.payments.base import PaymentIntent, WebhookEvent
from app.integrations.payments.factory import get_payment_provider
from app.models.course import Course
from app.models.enums import PaymentStatus, PurchaseStatus
from app.models.payment import Payment
from app.models.purchase import Purchase
from app.models.user import User
from app.repositories.payment_repository import PaymentRepository
from app.repositories.purchase_repository import PurchaseRepository
from app.services.enrollment_service import EnrollmentService
from app.services.notification_service import NotificationService

logger = logging.getLogger("sevanna")

# Payment statuses that mean "successfully paid".
_APPROVED = {PaymentStatus.APPROVED}
# Terminal failure statuses.
_FAILED = {PaymentStatus.DECLINED, PaymentStatus.ERROR, PaymentStatus.VOIDED}


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.provider = get_payment_provider()
        self.payments = PaymentRepository(session)
        self.purchases = PurchaseRepository(session)
        self.enrollments = EnrollmentService(session)

    # ------------------------------------------------------------------ #
    async def create_payment(self, *, purchase_id: uuid.UUID, user: User) -> Payment:
        purchase = await self.purchases.get_by_id_with_course(purchase_id)
        if purchase is None or purchase.user_id != user.id:
            raise NotFoundError("La compra solicitada no existe.", code="PURCHASE_NOT_FOUND")
        if purchase.status != PurchaseStatus.PENDING:
            raise BusinessRuleError(
                "Esta compra no está pendiente de pago.", code="PURCHASE_NOT_PENDING"
            )

        # Idempotent: reuse an in-flight payment for the same purchase.
        existing = await self.payments.get_by_purchase_id(purchase.id)
        if existing is not None:
            return existing

        reference = f"sev-{uuid.uuid4().hex}"
        creation = await self.provider.create_payment(
            PaymentIntent(
                reference=reference,
                amount=purchase.amount,
                currency=purchase.currency,
                description=f"Curso: {purchase.course.title}",
                customer_email=user.email,
                customer_name=user.full_name,
            )
        )

        payment = Payment(
            purchase_id=purchase.id,
            provider=self.provider.name,
            external_reference=reference,
            external_transaction_id=creation.external_transaction_id,
            amount=purchase.amount,
            currency=purchase.currency,
            status=creation.status,
            checkout_url=creation.checkout_url,
            raw_response=creation.raw or None,
        )
        self.payments.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def get_for_user(self, *, payment_id: uuid.UUID, user: User) -> Payment:
        payment = await self.payments.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError("El pago solicitado no existe.", code="PAYMENT_NOT_FOUND")
        purchase = await self.purchases.get_by_id(payment.purchase_id)
        if purchase is None or (purchase.user_id != user.id and not user.is_admin):
            raise NotFoundError("El pago solicitado no existe.", code="PAYMENT_NOT_FOUND")
        return payment

    # ------------------------------------------------------------------ #
    async def process_webhook(
        self, *, raw_body: bytes, headers: dict[str, str], background: BackgroundTasks
    ) -> tuple[bool, str]:
        """Authenticate and process a provider webhook. Returns (processed, detail).

        Raises ``InvalidWebhookError`` on bad signature/payload; the router maps
        that to a 422 (INVALID_WEBHOOK) so spoofed requests are rejected.
        """
        event: WebhookEvent = self.provider.verify_and_parse_webhook(
            raw_body=raw_body, headers=headers
        )

        # Locate our payment by the reference we generated (fallback: tx id).
        payment = None
        if event.reference:
            payment = await self.payments.get_by_reference(event.reference)
        if payment is None and event.external_transaction_id:
            payment = await self.payments.get_by_transaction_id(
                event.external_transaction_id
            )
        if payment is None:
            logger.warning(
                "webhook for unknown payment",
                extra={"event": "webhook_unknown", "request_id": None},
            )
            return False, "unknown_reference"

        # Lock the purchase row so concurrent webhooks serialize on it.
        locked_purchase = (
            await self.session.execute(
                select(Purchase)
                .where(Purchase.id == payment.purchase_id)
                .with_for_update()
            )
        ).scalar_one()

        # Idempotency: if already settled to PAID, do nothing further.
        if locked_purchase.status == PurchaseStatus.PAID:
            await self.session.commit()
            return False, "already_processed"

        # Record the transaction id / raw payload on the payment.
        if event.external_transaction_id:
            payment.external_transaction_id = event.external_transaction_id
        payment.status = event.status
        payment.raw_response = event.raw or payment.raw_response

        detail = event.status.value
        if event.status in _APPROVED:
            await self._settle_paid(locked_purchase, background)
            detail = "paid"
        elif event.status in _FAILED:
            if locked_purchase.status == PurchaseStatus.PENDING:
                locked_purchase.status = PurchaseStatus.FAILED
            detail = "failed"

        await self.session.commit()
        return True, detail

    async def _settle_paid(
        self, purchase: Purchase, background: BackgroundTasks
    ) -> None:
        purchase.status = PurchaseStatus.PAID
        # Create the enrollment (idempotent) inside the same transaction.
        await self.enrollments.activate_for_purchase(purchase)

        # Load course + user for the confirmation email.
        course = await self.session.get(Course, purchase.course_id)
        user = await self.session.get(User, purchase.user_id)
        if course is not None and user is not None:
            NotificationService.schedule_purchase_confirmation(
                background, user=user, course=course
            )
