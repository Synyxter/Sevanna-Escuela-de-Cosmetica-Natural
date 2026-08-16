from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def update_profile(self, user: User, *, full_name: str | None) -> User:
        if full_name is not None:
            user.full_name = full_name.strip()
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def list_users(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        return await self.users.list_paginated(offset=offset, limit=limit)
