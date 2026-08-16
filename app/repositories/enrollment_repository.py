from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus


class EnrollmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, enrollment_id: uuid.UUID) -> Enrollment | None:
        stmt = (
            select(Enrollment)
            .options(joinedload(Enrollment.course))
            .where(Enrollment.id == enrollment_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_purchase_id(self, purchase_id: uuid.UUID) -> Enrollment | None:
        stmt = select(Enrollment).where(Enrollment.purchase_id == purchase_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_active(
        self, user_id: uuid.UUID, course_id: uuid.UUID
    ) -> Enrollment | None:
        stmt = select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        return (await self.session.execute(stmt)).scalars().first()

    def add(self, enrollment: Enrollment) -> None:
        self.session.add(enrollment)

    async def list_all(
        self, *, offset: int, limit: int
    ) -> tuple[list[Enrollment], int]:
        total = (
            await self.session.execute(select(func.count(Enrollment.id)))
        ).scalar_one()
        stmt = (
            select(Enrollment)
            .options(joinedload(Enrollment.course), joinedload(Enrollment.user))
            .order_by(Enrollment.enrolled_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).unique().scalars().all())
        return rows, total

    async def list_active_for_user(
        self, user_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[Enrollment], int]:
        base = select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        total = (
            await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        stmt = (
            base.options(joinedload(Enrollment.course))
            .order_by(Enrollment.enrolled_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).unique().scalars().all())
        return rows, total
