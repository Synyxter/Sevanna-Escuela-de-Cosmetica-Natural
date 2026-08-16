"""Purchase service — creates the commercial record of acquiring a course.

Enforces critical business rules:
- Rule 1: cannot purchase a non-existent course.
- Rule 3: only PUBLISHED courses are purchasable.
- Rule 4/30: the price is captured from the backend AT PURCHASE TIME and frozen
  on the Purchase; later course price changes never affect historical purchases.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.enums import CourseStatus, PurchaseStatus
from app.models.purchase import Purchase
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.repositories.purchase_repository import PurchaseRepository


class PurchaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.purchases = PurchaseRepository(session)
        self.courses = CourseRepository(session)

    async def create_purchase(self, *, user: User, course_id: uuid.UUID) -> Purchase:
        course = await self.courses.get_by_id(course_id)
        if course is None or course.status == CourseStatus.ARCHIVED:
            raise NotFoundError("El curso solicitado no existe.", code="COURSE_NOT_FOUND")
        if course.status != CourseStatus.PUBLISHED:
            raise BusinessRuleError(
                "El curso no está disponible para compra.", code="COURSE_NOT_PURCHASABLE"
            )

        # Already owns the course.
        if await self.purchases.has_paid_purchase(user.id, course_id):
            raise BusinessRuleError(
                "Ya adquiriste este curso.", code="ALREADY_PURCHASED"
            )

        # Reuse an existing pending purchase to avoid duplicates on retries.
        existing = await self.purchases.get_pending_for_user_course(user.id, course_id)
        if existing is not None:
            return existing

        purchase = Purchase(
            user_id=user.id,
            course_id=course.id,
            amount=course.price,  # frozen price
            currency=course.currency,
            status=PurchaseStatus.PENDING,
        )
        self.purchases.add(purchase)
        await self.session.commit()
        await self.session.refresh(purchase)
        return purchase

    async def get_for_user(self, *, purchase_id: uuid.UUID, user: User) -> Purchase:
        purchase = await self.purchases.get_by_id_with_course(purchase_id)
        if purchase is None or (purchase.user_id != user.id and not user.is_admin):
            raise NotFoundError("La compra solicitada no existe.", code="PURCHASE_NOT_FOUND")
        return purchase

    async def list_for_user(
        self, *, user: User, offset: int, limit: int
    ) -> tuple[list[Purchase], int]:
        return await self.purchases.list_for_user(user.id, offset=offset, limit=limit)
