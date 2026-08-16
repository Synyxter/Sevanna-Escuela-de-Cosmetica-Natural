from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_reference(self, reference: str) -> Payment | None:
        stmt = (
            select(Payment)
            .options(joinedload(Payment.purchase))
            .where(Payment.external_reference == reference)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_transaction_id(self, transaction_id: str) -> Payment | None:
        stmt = (
            select(Payment)
            .options(joinedload(Payment.purchase))
            .where(Payment.external_transaction_id == transaction_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_purchase_id(self, purchase_id: uuid.UUID) -> Payment | None:
        stmt = select(Payment).where(Payment.purchase_id == purchase_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def add(self, payment: Payment) -> None:
        self.session.add(payment)
