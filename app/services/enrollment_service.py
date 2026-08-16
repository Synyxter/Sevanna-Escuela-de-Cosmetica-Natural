"""Enrollment service — grants and validates access to purchased courses.

Enforces:
- Rule 2: access only exists when a PAID purchase + ACTIVE enrollment exist.
- Rule 8: a paid purchase yields exactly one enrollment (idempotent).
- Rule 9: an active enrollment's owner may retrieve the private WhatsApp/Meet links.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, BusinessRuleError, NotFoundError
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus
from app.models.purchase import Purchase
from app.models.user import User
from app.repositories.enrollment_repository import EnrollmentRepository


class EnrollmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.enrollments = EnrollmentRepository(session)

    async def activate_for_purchase(self, purchase: Purchase) -> Enrollment:
        """Create (or return the existing) active enrollment for a paid purchase.

        Idempotent: safe to call multiple times (e.g. duplicate webhooks) — it
        will never create two enrollments for the same purchase.
        """
        existing = await self.enrollments.get_by_purchase_id(purchase.id)
        if existing is not None:
            return existing

        enrollment = Enrollment(
            user_id=purchase.user_id,
            course_id=purchase.course_id,
            purchase_id=purchase.id,
            status=EnrollmentStatus.ACTIVE,
        )
        self.enrollments.add(enrollment)
        # Flush (not commit) so the caller's transaction stays atomic.
        await self.session.flush()
        return enrollment

    async def get_for_user(
        self, *, enrollment_id: uuid.UUID, user: User
    ) -> Enrollment:
        enrollment = await self.enrollments.get_by_id(enrollment_id)
        if enrollment is None or (enrollment.user_id != user.id and not user.is_admin):
            raise NotFoundError(
                "La inscripción solicitada no existe.", code="ENROLLMENT_NOT_FOUND"
            )
        return enrollment

    async def list_my_courses(
        self, *, user: User, offset: int, limit: int
    ) -> tuple[list[Enrollment], int]:
        return await self.enrollments.list_active_for_user(
            user.id, offset=offset, limit=limit
        )

    async def list_all(
        self, *, offset: int, limit: int
    ) -> tuple[list[Enrollment], int]:
        return await self.enrollments.list_all(offset=offset, limit=limit)

    async def get_access_links(
        self, *, enrollment_id: uuid.UUID, user: User
    ) -> tuple[str | None, str | None]:
        enrollment = await self.enrollments.get_by_id(enrollment_id)
        if enrollment is None:
            raise NotFoundError(
                "La inscripción solicitada no existe.", code="ENROLLMENT_NOT_FOUND"
            )
        # Ownership check — never trust a client-supplied user id.
        if enrollment.user_id != user.id:
            raise AuthorizationError("No tienes acceso a esta inscripción.")
        if enrollment.status != EnrollmentStatus.ACTIVE:
            raise BusinessRuleError(
                "La inscripción no está activa.", code="ENROLLMENT_NOT_ACTIVE"
            )
        course = enrollment.course
        return course.whatsapp_group_url, course.google_meet_url
