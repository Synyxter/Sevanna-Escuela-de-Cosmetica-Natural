"""Seed script — bootstraps the first admin and sample catalog data.

Idempotent: running it multiple times will not create duplicates. Intended for
local development / first deploy. Run with:

    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from slugify import slugify

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.category import Category
from app.models.course import Course
from app.models.enums import CourseLevel, CourseModality, CourseStatus, UserRole
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.user_repository import UserRepository


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        users = UserRepository(session)
        categories = CategoryRepository(session)

        # --- First admin ---
        admin = await users.get_by_email(settings.first_admin_email)
        if admin is None:
            admin = User(
                full_name=settings.first_admin_name,
                email=settings.first_admin_email.lower(),
                password_hash=hash_password(settings.first_admin_password),
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True,
            )
            session.add(admin)
            print(f"Created admin: {settings.first_admin_email}")
        else:
            print("Admin already exists — skipping.")

        # --- Sample categories ---
        sample_categories = ["Jabonería", "Velas", "Cosmética facial", "Maquillaje natural"]
        category_map: dict[str, Category] = {}
        for name in sample_categories:
            existing = await categories.get_by_name(name)
            if existing is None:
                existing = Category(name=name, slug=slugify(name))
                session.add(existing)
            category_map[name] = existing
        await session.flush()

        # --- Sample published course ---
        from sqlalchemy import select

        jabon_slug = "elaboracion-de-jabones"
        already = (
            await session.execute(select(Course).where(Course.slug == jabon_slug))
        ).scalar_one_or_none()
        if already is None:
            session.add(
                Course(
                    title="Elaboración de Jabones Artesanales",
                    slug=jabon_slug,
                    short_description="Aprende a crear jabones naturales desde cero.",
                    description="Curso completo de saponificación en frío y técnicas naturales.",
                    objective="Dominar la elaboración de jabones artesanales seguros y bellos.",
                    modality=CourseModality.HYBRID,
                    level=CourseLevel.BEGINNER,
                    duration="4 semanas",
                    price=Decimal("150000.00"),
                    currency="COP",
                    materials={
                        "included": ["Guía PDF", "Plantillas de recetas"],
                        "required": ["Aceites base", "Soda cáustica", "Moldes"],
                    },
                    learning_outcomes=[
                        "Entender la saponificación",
                        "Formular recetas propias",
                    ],
                    status=CourseStatus.PUBLISHED,
                    whatsapp_group_url="https://chat.whatsapp.com/ejemplo",
                    google_meet_url="https://meet.google.com/ejemplo",
                    category_id=category_map["Jabonería"].id,
                )
            )
            print(f"Created sample course: {jabon_slug}")

        await session.commit()
        print("Seed completed.")


if __name__ == "__main__":
    asyncio.run(seed())
