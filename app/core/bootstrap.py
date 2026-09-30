"""Startup data bootstrap.

On application startup (see ``main.lifespan``) this ensures the deployment is
usable out of the box:

- Creates the initial admin (from settings) if it does not exist.
- Syncs the course catalog from ``scripts/catalog_data.json``: creates any
  missing categories/courses (so a fresh production database, e.g. a new
  managed PostgreSQL on Render, is populated on first boot), backfills missing
  course images and retires courses listed in ``removed_slugs``. Existing data
  and admin edits are never overwritten.

Both steps are idempotent and never raise into startup: any failure is logged
and the API still comes up. Disable with ``AUTO_SEED=false``.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.course import Course
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger("sevanna")


async def bootstrap_data() -> None:
    if not settings.auto_seed:
        return
    try:
        async with AsyncSessionLocal() as session:
            users = UserRepository(session)
            if await users.get_by_email(settings.first_admin_email) is None:
                session.add(
                    User(
                        full_name=settings.first_admin_name,
                        email=settings.first_admin_email.lower(),
                        password_hash=hash_password(settings.first_admin_password),
                        role=UserRole.ADMIN,
                        is_active=True,
                        email_verified=True,
                    )
                )
                await session.commit()
                logger.info("bootstrap: admin created", extra={"event": "bootstrap_admin"})

            course_count = (
                await session.execute(select(func.count(Course.id)))
            ).scalar_one()

        # Sync the catalog on every boot. It is idempotent: creates only missing
        # categories/courses and backfills missing images, never duplicating or
        # overwriting admin edits. Import lazily to avoid coupling app import to
        # the scripts package.
        from scripts.seed_catalog import seed_catalog

        await seed_catalog()
        logger.info(
            "bootstrap: catalog synced",
            extra={"event": "bootstrap_catalog", "courses_before": course_count},
        )
    except Exception:  # noqa: BLE001 - never block startup on seeding
        logger.exception("bootstrap_data failed (API will still start)")
