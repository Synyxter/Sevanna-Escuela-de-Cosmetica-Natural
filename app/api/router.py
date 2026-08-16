"""Aggregates all v1 routers under the versioned API prefix."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    categories,
    courses,
    enrollments,
    health,
    payments,
    purchases,
    users,
)
from app.core.config import settings

api_router = APIRouter(prefix=settings.api_v1_prefix)

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(courses.router)
api_router.include_router(categories.router)
api_router.include_router(purchases.router)
api_router.include_router(payments.router)
api_router.include_router(enrollments.router)
api_router.include_router(admin.router)
