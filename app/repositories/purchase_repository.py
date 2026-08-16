from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.enums import PurchaseStatus
from app.models.purchase import Purchase


class PurchaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, purchase_id: uuid.UUID) -> Purchase | None:
        return await self.session.get(Purchase, purchase_id)

    async def get_by_id_with_course(self, purchase_id: uuid.UUID) -> Purchase | None:
        stmt = (
            select(Purchase)
            .options(joinedload(Purchase.course))
            .where(Purchase.id == purchase_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_pending_for_user_course(
        self, user_id: uuid.UUID, course_id: uuid.UUID
    ) -> Purchase | None:
        stmt = select(Purchase).where(
            Purchase.user_id == user_id,
            Purchase.course_id == course_id,
            Purchase.status == PurchaseStatus.PENDING,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def has_paid_purchase(self, user_id: uuid.UUID, course_id: uuid.UUID) -> bool:
        stmt = select(Purchase.id).where(
            Purchase.user_id == user_id,
            Purchase.course_id == course_id,
            Purchase.status == PurchaseStatus.PAID,
        )
        return (await self.session.execute(stmt)).first() is not None

    def add(self, purchase: Purchase) -> None:
        self.session.add(purchase)

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[Purchase], int]:
        base = select(Purchase).where(Purchase.user_id == user_id)
        total = (
            await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        stmt = (
            base.options(joinedload(Purchase.course))
            .order_by(Purchase.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).unique().scalars().all())
        return rows, total

    async def list_all(
        self, *, offset: int, limit: int
    ) -> tuple[list[Purchase], int]:
        total = (await self.session.execute(select(func.count(Purchase.id)))).scalar_one()
        stmt = (
            select(Purchase)
            .options(joinedload(Purchase.course), joinedload(Purchase.user))
            .order_by(Purchase.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).unique().scalars().all())
        return rows, total
