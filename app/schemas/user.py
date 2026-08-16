from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Only fields a user is allowed to change on their own profile."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
