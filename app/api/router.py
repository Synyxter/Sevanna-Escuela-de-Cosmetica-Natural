"""Aggregates all v1 routers under the versioned API prefix.

Sevanna is a course catalog: the payment/enrollment ("commerce") and the
student-account ("accounts") modules are DISABLED by default and only mounted
when their feature flag is on (see app/core/config.py). The code for those
modules is kept intact so they can be reactivated in the future without a
rewrite. Admin sign-in and course/category management are always active.
"""

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

# --- Always active (catalog + admin course management) ---
api_router.include_router(health.router)
api_router.include_router(auth.router)  # admin login / refresh / logout
api_router.include_router(courses.router)
api_router.include_router(categories.router)
api_router.include_router(admin.router)  # course + category administration

# --- Accounts module (student accounts) — opt-in via ENABLE_ACCOUNTS ---
if settings.enable_accounts:
    api_router.include_router(auth.accounts_router)  # register / verify / reset
    api_router.include_router(users.router)  # /users/me ...
    api_router.include_router(admin.accounts_router)  # admin: list users

# --- Commerce module (purchases / payments / enrollments) — ENABLE_COMMERCE ---
if settings.enable_commerce:
    api_router.include_router(purchases.router)
    api_router.include_router(payments.router)
    api_router.include_router(enrollments.router)
    api_router.include_router(admin.commerce_router)  # admin: purchases, enrollments
