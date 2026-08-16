from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import EnrollmentStatus, PurchaseStatus


class AdminPurchaseItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: str
    course_id: uuid.UUID
    course_title: str
    amount: Decimal
    currency: str
    status: PurchaseStatus
    created_at: datetime


class AdminEnrollmentItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    course_id: uuid.UUID
    course_title: str
    status: EnrollmentStatus
    enrolled_at: datetime
