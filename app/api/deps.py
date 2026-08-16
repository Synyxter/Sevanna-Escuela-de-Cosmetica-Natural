"""Shared FastAPI dependencies: DB session, authenticated user, admin guard.

Identity is always derived from the verified JWT — never from a client-supplied
user id (Rule 69). Access tokens only (refresh tokens cannot access resources).
"""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

DBSession = Annotated[AsyncSession, Depends(get_db)]

# auto_error=False so we can raise our own consistent error envelope.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Se requiere autenticación.")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("La sesión expiró.", code="TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token inválido.", code="INVALID_TOKEN") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Tipo de token inválido.", code="INVALID_TOKEN")

    subject = payload.get("sub")
    try:
        user_id = uuid.UUID(str(subject))
    except (ValueError, TypeError) as exc:
        raise AuthenticationError("Token inválido.", code="INVALID_TOKEN") from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("La cuenta no está disponible.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise AuthorizationError("Se requieren privilegios de administrador.")
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
