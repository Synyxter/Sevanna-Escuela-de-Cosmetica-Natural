"""Seed the course catalog from ``scripts/catalog_data.json``.

Idempotent: creates any missing categories and courses; skips items that already
exist (categories by name, courses by generated slug). Run with:

    python -m scripts.seed_catalog
"""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from slugify import slugify

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.course import Course
from app.models.enums import CourseLevel, CourseModality, CourseStatus
from app.repositories.category_repository import CategoryRepository
from app.repositories.course_repository import CourseRepository

DATA_FILE = Path(__file__).parent / "catalog_data.json"


async def seed_catalog() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as session:
        categories = CategoryRepository(session)
        courses = CourseRepository(session)

        # --- Categories (idempotent by name) ---
        name_to_id: dict[str, object] = {}
        created_cats = 0
        for name in data["categories"]:
            existing = await categories.get_by_name(name)
            if existing is None:
                slug = slugify(name)
                if await categories.get_by_slug(slug):
                    slug = f"{slug}-{slugify(name)[:4]}"
                existing = Category(name=name, slug=slug)
                categories.add(existing)
                await session.flush()
                created_cats += 1
            name_to_id[name] = existing.id

        # --- Courses (idempotent by slug) ---
        created_courses = 0
        skipped = 0
        images_filled = 0
        for item in data["courses"]:
            slug = slugify(item["title"])
            existing = await courses.get_by_slug(slug)
            if existing:
                # Backfill the image for courses created before images existed;
                # never overwrite an image set later (e.g. by the admin).
                if existing.image_url is None and item.get("image_url"):
                    existing.image_url = item["image_url"]
                    images_filled += 1
                skipped += 1
                continue
            course = Course(
                title=item["title"],
                slug=slug,
                short_description=item.get("short_description"),
                description=item.get("description"),
                objective=item.get("objective"),
                image_url=item.get("image_url"),
                modality=CourseModality(item["modality"]),
                level=CourseLevel(item["level"]),
                duration=item.get("duration"),
                price=Decimal(str(item["price"])),
                currency=item.get("currency", "COP"),
                materials=item.get("materials"),
                learning_outcomes=item.get("learning_outcomes"),
                status=CourseStatus(item.get("status", "PUBLISHED")),
                category_id=name_to_id.get(item["category"]),
            )
            courses.add(course)
            created_courses += 1

        await session.commit()
        print(
            f"Categorías creadas: {created_cats} | "
            f"Cursos creados: {created_courses} | Cursos omitidos (ya existían): {skipped} | "
            f"Imágenes asignadas: {images_filled}"
        )


if __name__ == "__main__":
    asyncio.run(seed_catalog())
