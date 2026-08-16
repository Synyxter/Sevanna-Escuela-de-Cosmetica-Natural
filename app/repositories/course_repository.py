from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.category import Category
from app.models.course import Course
from app.models.enums import CourseLevel, CourseModality, CourseStatus
from app.schemas.course import CourseFilterParams

# Whitelisted sortable columns to prevent arbitrary/unsafe ordering.
_SORTABLE = {
    "created_at": Course.created_at,
    "price": Course.price,
    "title": Course.title,
}


class CourseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, course_id: uuid.UUID) -> Course | None:
        stmt = (
            select(Course)
            .options(joinedload(Course.category))
            .where(Course.id == course_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_slug(self, slug: str, *, published_only: bool = False) -> Course | None:
        stmt = (
            select(Course)
            .options(joinedload(Course.category))
            .where(Course.slug == slug)
        )
        if published_only:
            stmt = stmt.where(Course.status == CourseStatus.PUBLISHED)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Course.id).where(Course.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Course.id != exclude_id)
        return (await self.session.execute(stmt)).first() is not None

    def add(self, course: Course) -> None:
        self.session.add(course)

    def _apply_filters(
        self, stmt: Select, filters: CourseFilterParams, *, published_only: bool
    ) -> Select:
        if published_only:
            stmt = stmt.where(Course.status == CourseStatus.PUBLISHED)
        if filters.search:
            pattern = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Course.title).like(pattern),
                    func.lower(Course.short_description).like(pattern),
                )
            )
        if filters.level:
            stmt = stmt.where(Course.level == CourseLevel(filters.level))
        if filters.modality:
            stmt = stmt.where(Course.modality == CourseModality(filters.modality))
        if filters.category:
            stmt = stmt.join(Course.category).where(Category.slug == filters.category)
        return stmt

    async def list_catalog(
        self, filters: CourseFilterParams, *, published_only: bool = True
    ) -> tuple[list[Course], int]:
        # Count with the same filters (without eager loads/order).
        count_stmt = self._apply_filters(
            select(func.count(Course.id)), filters, published_only=published_only
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = self._apply_filters(
            select(Course).options(joinedload(Course.category)),
            filters,
            published_only=published_only,
        )

        # Safe sorting from a whitelist.
        sort_key = filters.sort.lstrip("-")
        column = _SORTABLE.get(sort_key, Course.created_at)
        column = column.desc() if filters.sort.startswith("-") else column.asc()
        stmt = stmt.order_by(column).offset(filters.offset).limit(filters.limit)

        rows = list((await self.session.execute(stmt)).unique().scalars().all())
        return rows, total

    async def list_admin(
        self, *, offset: int, limit: int
    ) -> tuple[list[Course], int]:
        """All courses regardless of status (admin view)."""
        total = (await self.session.execute(select(func.count(Course.id)))).scalar_one()
        stmt = (
            select(Course)
            .options(joinedload(Course.category))
            .order_by(Course.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.session.execute(stmt)).unique().scalars().all())
        return rows, total

    async def list_featured(self, limit: int = 6) -> list[Course]:
        stmt = (
            select(Course)
            .options(joinedload(Course.category))
            .where(Course.status == CourseStatus.PUBLISHED)
            .order_by(Course.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).unique().scalars().all())
