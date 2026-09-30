from __future__ import annotations

import json
from decimal import Decimal

import pytest
import scripts.seed_catalog as seed_module
from sqlalchemy import func, select

from app.models.course import Course
from app.models.enums import (
    CourseLevel,
    CourseModality,
    CourseStatus,
    PurchaseStatus,
    UserRole,
)
from app.models.purchase import Purchase
from app.models.user import User
from tests.conftest import TestSessionLocal

pytestmark = pytest.mark.asyncio

DATA = json.loads(seed_module.DATA_FILE.read_text(encoding="utf-8"))
REMOVED = "curso-de-velas-fenol"


def _fenol() -> Course:
    return Course(
        title="Curso de Velas Fenol",
        slug=REMOVED,
        modality=CourseModality.HYBRID,
        level=CourseLevel.INTERMEDIATE,
        price=Decimal("350000.00"),
        currency="COP",
        status=CourseStatus.PUBLISHED,
    )


@pytest.fixture(autouse=True)
def _use_test_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seed_module, "AsyncSessionLocal", TestSessionLocal)


async def test_sync_creates_catalog_and_removes_listed_course() -> None:
    async with TestSessionLocal() as s:
        s.add(_fenol())
        await s.commit()

    await seed_module.seed_catalog()

    async with TestSessionLocal() as s:
        total = (await s.execute(select(func.count(Course.id)))).scalar_one()
        fenol = (
            await s.execute(select(Course).where(Course.slug == REMOVED))
        ).scalar_one_or_none()
        bisuteria = (
            await s.execute(select(Course).where(Course.slug == "curso-de-bisuteria"))
        ).scalar_one()

    assert total == len(DATA["courses"])
    assert fenol is None
    assert bisuteria.price == Decimal("250000.00")
    assert bisuteria.image_url == "/images/cursos/curso33.jpg"


async def test_sync_is_idempotent() -> None:
    await seed_module.seed_catalog()
    await seed_module.seed_catalog()
    async with TestSessionLocal() as s:
        total = (await s.execute(select(func.count(Course.id)))).scalar_one()
    assert total == len(DATA["courses"])


async def test_removed_course_with_history_is_archived_not_deleted() -> None:
    async with TestSessionLocal() as s:
        user = User(
            full_name="Estudiante",
            email="hist@test.co",
            password_hash="x",
            role=UserRole.STUDENT,
        )
        course = _fenol()
        s.add_all([user, course])
        await s.flush()
        s.add(
            Purchase(
                user_id=user.id,
                course_id=course.id,
                amount=Decimal("350000.00"),
                currency="COP",
                status=PurchaseStatus.PAID,
            )
        )
        await s.commit()

    await seed_module.seed_catalog()

    async with TestSessionLocal() as s:
        fenol = (await s.execute(select(Course).where(Course.slug == REMOVED))).scalar_one()
    assert fenol.status == CourseStatus.ARCHIVED
