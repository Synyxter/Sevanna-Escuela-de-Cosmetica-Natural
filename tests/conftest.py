"""Test fixtures.

Runs the suite against an in-memory SQLite database (async) using the same ORM
models. A StaticPool keeps a single shared connection so all sessions see the
same in-memory schema/data. The payment/email providers default to
``fake``/``console`` (see Settings defaults), so no external services are hit.
"""

from __future__ import annotations

import os

# The accounts/commerce modules are disabled by default (catalog-only backend).
# Enable them BEFORE importing the app so their routers are mounted and the
# suite keeps exercising the preserved code. Must run before app.core.config
# instantiates its cached settings.
os.environ.setdefault("ENABLE_ACCOUNTS", "true")
os.environ.setdefault("ENABLE_COMMERCE", "true")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

# Disable rate limiting during tests (state is process-global otherwise).
settings.rate_limit_enabled = False

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _setup_database(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
    # Background email tasks open their own session — point them at the test DB.
    monkeypatch.setattr(
        "app.services.email_service.AsyncSessionLocal", TestSessionLocal
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# User / auth helpers
# --------------------------------------------------------------------------- #
async def _create_user(*, email: str, password: str, role) -> object:
    from app.core.security import hash_password
    from app.models.user import User

    async with TestSessionLocal() as s:
        user = User(
            full_name="Test User",
            email=email.lower(),
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        return user


def _auth_headers(user_id) -> dict[str, str]:
    from app.core.security import create_access_token

    token, _, _ = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_user():
    from app.models.enums import UserRole

    return await _create_user(
        email="admin@test.co", password="AdminPass123", role=UserRole.ADMIN
    )


@pytest_asyncio.fixture
async def student_user():
    from app.models.enums import UserRole

    return await _create_user(
        email="student@test.co", password="StudentPass123", role=UserRole.STUDENT
    )


@pytest.fixture
def admin_headers(admin_user) -> dict[str, str]:
    return _auth_headers(admin_user.id)


@pytest.fixture
def student_headers(student_user) -> dict[str, str]:
    return _auth_headers(student_user.id)
