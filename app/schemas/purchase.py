from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import PurchaseStatus


class PurchaseCreateRequest(BaseModel):
    course_id: uuid.UUID


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    amount: Decimal
    currency: str
    status: PurchaseStatus
    created_at: datetime


class PurchaseWithCourseResponse(PurchaseResponse):
    course_title: str
    course_slug: str
