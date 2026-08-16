"""Controlled vocabularies shared by models and schemas.

These string values are the stable API contract. The frontend is free to
translate them for display (e.g. BEGINNER -> "Básico") but the API always
returns the canonical value regardless of presentation language.
"""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"
    # Reserved for future expansion (schema already supports them):
    TEACHER = "TEACHER"
    MANAGER = "MANAGER"
    SUPPORT = "SUPPORT"


class CourseModality(str, enum.Enum):
    PRESENTIAL = "PRESENTIAL"
    ONLINE = "ONLINE"
    HYBRID = "HYBRID"


class CourseLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class CourseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class PurchaseStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    ERROR = "ERROR"
    VOIDED = "VOIDED"
    REFUNDED = "REFUNDED"


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class EmailStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
