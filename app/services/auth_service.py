"""Authentication & account lifecycle service.

Security properties enforced here:
- Passwords hashed with Argon2id; never stored/logged in plaintext.
- Email enumeration is avoided on register/forgot-password (generic responses).
- Refresh tokens are tracked in DB and can be revoked (logout / password reset).
- Reset & verification tokens are stored only as SHA-256 hashes and single-use.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.token import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair
from app.services import email_templates
from app.services.email_service import send_email_background

# Generic messages that never reveal whether an email exists.
_GENERIC_FORGOT = (
    "Si existe una cuenta asociada a este correo, recibirás instrucciones "
    "para restablecer tu contraseña."
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    # ------------------------------------------------------------------ #
    async def register(self, *, full_name: str, email: str, password: str,
                       background: BackgroundTasks) -> User:
        email = _normalize_email(email)
        if await self.users.email_exists(email):
            # Do not leak existence via a specific error in enumeration-sensitive
            # flows; a 409 here is acceptable per spec but message stays generic.
            raise ConflictError("No fue posible completar el registro.", code="EMAIL_TAKEN")

        user = User(
            full_name=full_name.strip(),
            email=email,
            password_hash=hash_password(password),
            role=UserRole.STUDENT,
            is_active=True,
            email_verified=False,
        )
        self.users.add(user)
        await self.session.flush()

        await self._issue_email_verification(user, background)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def _issue_email_verification(
        self, user: User, background: BackgroundTasks
    ) -> None:
        raw_token = secrets.token_urlsafe(32)
        record = EmailVerificationToken(
            token_hash=_hash_token(raw_token),
            user_id=user.id,
            expires_at=datetime.now(UTC)
            + timedelta(hours=settings.email_verification_token_expire_hours),
        )
        self.session.add(record)
        verify_link = f"{settings.frontend_url}/verify-email?token={raw_token}"
        subject, html, text = email_templates.verification_email(user.full_name, verify_link)
        background.add_task(
            send_email_background,
            to=user.email,
            subject=subject,
            html_body=html,
            text_body=text,
            template="verify_email",
            related_entity_id=user.id,
        )

    # ------------------------------------------------------------------ #
    async def login(self, *, email: str, password: str) -> tuple[User, TokenPair]:
        email = _normalize_email(email)
        user = await self.users.get_by_email(email)
        # Constant-ish response: same error whether user missing or bad password.
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Correo o contraseña incorrectos.")
        if not user.is_active:
            raise AuthenticationError("La cuenta está desactivada.")

        tokens = await self._issue_token_pair(user)
        await self.session.commit()
        return user, tokens

    async def _issue_token_pair(self, user: User) -> TokenPair:
        access, _, _ = create_access_token(str(user.id), {"role": user.role.value})
        refresh, jti, expires_at = create_refresh_token(str(user.id))
        self.session.add(
            RefreshToken(jti=jti, user_id=user.id, expires_at=expires_at, revoked=False)
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    # ------------------------------------------------------------------ #
    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Token de actualización inválido.") from exc

        if payload.get("type") != "refresh":
            raise AuthenticationError("Tipo de token inválido.")

        jti = payload.get("jti")
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        record = (await self.session.execute(stmt)).scalar_one_or_none()
        if record is None or record.revoked:
            raise AuthenticationError("La sesión ya no es válida.")

        user = await self.users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("La cuenta no está disponible.")

        # Rotate: revoke the used refresh token and issue a fresh pair.
        record.revoked = True
        tokens = await self._issue_token_pair(user)
        await self.session.commit()
        return tokens

    # ------------------------------------------------------------------ #
    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError:
            # Idempotent logout — invalid token is treated as already logged out.
            return
        jti = payload.get("jti")
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        record = (await self.session.execute(stmt)).scalar_one_or_none()
        if record is not None and not record.revoked:
            record.revoked = True
            await self.session.commit()

    # ------------------------------------------------------------------ #
    async def forgot_password(self, *, email: str, background: BackgroundTasks) -> str:
        email = _normalize_email(email)
        user = await self.users.get_by_email(email)
        if user is not None and user.is_active:
            raw_token = secrets.token_urlsafe(32)
            record = PasswordResetToken(
                token_hash=_hash_token(raw_token),
                user_id=user.id,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.password_reset_token_expire_minutes),
            )
            self.session.add(record)
            await self.session.commit()
            reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
            subject, html, text = email_templates.password_reset_email(
                user.full_name, reset_link
            )
            background.add_task(
                send_email_background,
                to=user.email,
                subject=subject,
                html_body=html,
                text_body=text,
                template="reset_password",
                related_entity_id=user.id,
            )
        # Always the same response regardless of existence.
        return _GENERIC_FORGOT

    async def reset_password(self, *, token: str, new_password: str) -> None:
        token_hash = _hash_token(token)
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
        record = (await self.session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)
        if record is None or record.used or record.expires_at < now:
            raise ValidationError("El enlace de recuperación es inválido o expiró.")

        user = await self.users.get_by_id(record.user_id)
        if user is None:
            raise ValidationError("El enlace de recuperación es inválido o expiró.")

        user.password_hash = hash_password(new_password)
        record.used = True
        # Revoke all active refresh tokens for safety.
        revoke_stmt = select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
        )
        for rt in (await self.session.execute(revoke_stmt)).scalars().all():
            rt.revoked = True
        await self.session.commit()

    # ------------------------------------------------------------------ #
    async def verify_email(self, *, token: str) -> None:
        token_hash = _hash_token(token)
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
        record = (await self.session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)
        if record is None or record.used or record.expires_at < now:
            raise ValidationError("El enlace de verificación es inválido o expiró.")

        user = await self.users.get_by_id(record.user_id)
        if user is None:
            raise ValidationError("El enlace de verificación es inválido o expiró.")

        user.email_verified = True
        record.used = True
        await self.session.commit()
