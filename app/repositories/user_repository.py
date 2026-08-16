from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        # Case-insensitive lookup; emails are stored normalized (lowercase).
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        stmt = select(User.id).where(func.lower(User.email) == email.lower())
        return (await self.session.execute(stmt)).first() is not None

    def add(self, user: User) -> None:
        self.session.add(user)

    async def list_paginated(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        total = (await self.session.execute(select(func.count(User.id)))).scalar_one()
        stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        rows = list((await self.session.execute(stmt)).scalars().all())
        return rows, total
