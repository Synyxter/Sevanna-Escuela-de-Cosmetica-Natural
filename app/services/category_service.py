from __future__ import annotations

import uuid

from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.categories = CategoryRepository(session)

    async def list_categories(self) -> list[Category]:
        return await self.categories.list_all()

    async def get_or_404(self, category_id: uuid.UUID) -> Category:
        category = await self.categories.get_by_id(category_id)
        if category is None:
            raise NotFoundError("La categoría solicitada no existe.", code="CATEGORY_NOT_FOUND")
        return category

    async def create(self, *, name: str, description: str | None) -> Category:
        if await self.categories.get_by_name(name):
            raise ConflictError("Ya existe una categoría con ese nombre.", code="CATEGORY_EXISTS")
        slug = slugify(name)
        if await self.categories.get_by_slug(slug):
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        category = Category(name=name.strip(), slug=slug, description=description)
        self.categories.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category
