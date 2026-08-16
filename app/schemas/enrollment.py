from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CourseModality, EnrollmentStatus


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    purchase_id: uuid.UUID
    status: EnrollmentStatus
    enrolled_at: datetime


class MyCourseItem(BaseModel):
    """A course the authenticated user owns (via an active enrollment)."""

    enrollment_id: uuid.UUID
    course_id: uuid.UUID
    title: str
    slug: str
    image_url: str | None = None
    modality: CourseModality
    status: EnrollmentStatus
    enrolled_at: datetime


class EnrollmentAccessResponse(BaseModel):
    """Private access links — only for the enrollment's owner while ACTIVE."""

    whatsapp_url: str | None = None
    google_meet_url: str | None = None
