from __future__ import annotations

import uuid

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.course import Course
from app.models.purchase import Purchase
from app.repositories.category_repository import CategoryRepository
from app.repositories.course_repository import CourseRepository
from app.schemas.course import (
    CourseCreateRequest,
    CourseFilterParams,
    CourseUpdateRequest,
)


class CourseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.courses = CourseRepository(session)
        self.categories = CategoryRepository(session)

    # --- Public reads ------------------------------------------------- #
    async def list_catalog(
        self, filters: CourseFilterParams
    ) -> tuple[list[Course], int]:
        return await self.courses.list_catalog(filters, published_only=True)

    async def get_public_by_slug(self, slug: str) -> Course:
        course = await self.courses.get_by_slug(slug, published_only=True)
        if course is None:
            raise NotFoundError("El curso solicitado no existe.", code="COURSE_NOT_FOUND")
        return course

    async def list_featured(self, limit: int = 6) -> list[Course]:
        return await self.courses.list_featured(limit)

    async def list_admin(
        self, *, offset: int, limit: int
    ) -> tuple[list[Course], int]:
        return await self.courses.list_admin(offset=offset, limit=limit)

    # --- Admin reads -------------------------------------------------- #
    async def get_or_404(self, course_id: uuid.UUID) -> Course:
        course = await self.courses.get_by_id(course_id)
        if course is None:
            raise NotFoundError("El curso solicitado no existe.", code="COURSE_NOT_FOUND")
        return course

    # --- Admin writes ------------------------------------------------- #
    async def _unique_slug(self, base: str, *, exclude_id: uuid.UUID | None = None) -> str:
        slug = slugify(base)
        if not slug:
            slug = uuid.uuid4().hex[:8]
        if await self.courses.slug_exists(slug, exclude_id=exclude_id):
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        return slug

    async def _validate_category(self, category_id: uuid.UUID | None) -> None:
        if category_id is not None and await self.categories.get_by_id(category_id) is None:
            raise ValidationError("La categoría indicada no existe.", code="CATEGORY_NOT_FOUND")

    async def create_course(self, data: CourseCreateRequest) -> Course:
        await self._validate_category(data.category_id)
        slug = await self._unique_slug(data.slug or data.title)

        course = Course(
            title=data.title.strip(),
            slug=slug,
            short_description=data.short_description,
            description=data.description,
            objective=data.objective,
            image_url=data.image_url,
            modality=data.modality,
            level=data.level,
            duration=data.duration,
            price=data.price,
            currency=data.currency.upper(),
            materials=data.materials.model_dump() if data.materials else None,
            learning_outcomes=data.learning_outcomes,
            status=data.status,
            whatsapp_group_url=data.whatsapp_group_url,
            google_meet_url=data.google_meet_url,
            category_id=data.category_id,
        )
        self.courses.add(course)
        await self.session.commit()
        return await self.get_or_404(course.id)

    async def update_course(
        self, course_id: uuid.UUID, data: CourseUpdateRequest
    ) -> Course:
        course = await self.get_or_404(course_id)
        payload = data.model_dump(exclude_unset=True)

        if "category_id" in payload:
            await self._validate_category(payload["category_id"])

        if payload.get("slug"):
            course.slug = await self._unique_slug(payload["slug"], exclude_id=course.id)
            payload.pop("slug")

        if "materials" in payload and payload["materials"] is not None:
            payload["materials"] = (
                data.materials.model_dump() if data.materials else None
            )
        if payload.get("currency"):
            payload["currency"] = payload["currency"].upper()

        for field, value in payload.items():
            setattr(course, field, value)

        await self.session.commit()
        return await self.get_or_404(course.id)

    async def delete_course(self, course_id: uuid.UUID) -> None:
        course = await self.get_or_404(course_id)
        # Guard: don't hard-delete a course that has purchases (financial history).
        purchase_count = (
            await self.session.execute(
                select(func.count(Purchase.id)).where(Purchase.course_id == course_id)
            )
        ).scalar_one()
        if purchase_count:
            raise ConflictError(
                "No se puede eliminar un curso con compras asociadas. Archívalo.",
                code="COURSE_HAS_PURCHASES",
            )
        await self.session.delete(course)
        await self.session.commit()
