from __future__ import annotations

import pytest

from app.core.config import Settings


def _db_url(raw: str) -> str:
    return Settings(database_url=raw).database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgres://u:p@host:5432/db",
            "postgresql+asyncpg://u:p@host:5432/db",
        ),
        (
            "postgresql://u:p@host/db",
            "postgresql+asyncpg://u:p@host/db",
        ),
        (
            "postgresql+asyncpg://u:p@host/db",
            "postgresql+asyncpg://u:p@host/db",
        ),
        (
            "sqlite+aiosqlite:///./dev.db",
            "sqlite+aiosqlite:///./dev.db",
        ),
    ],
)
def test_database_url_scheme_is_normalized(raw: str, expected: str) -> None:
    assert _db_url(raw) == expected


def test_neon_url_is_adapted_for_asyncpg() -> None:
    raw = (
        "postgresql://neondb_owner:s3cr3t@ep-cool-name-123456.us-east-1.aws.neon.tech"
        "/neondb?sslmode=require&channel_binding=require"
    )
    assert _db_url(raw) == (
        "postgresql+asyncpg://neondb_owner:s3cr3t@ep-cool-name-123456.us-east-1.aws.neon.tech"
        "/neondb?ssl=require"
    )


def test_unrelated_query_params_are_kept() -> None:
    raw = "postgresql://u:p@host/db?sslmode=verify-full&application_name=sevanna"
    assert _db_url(raw) == (
        "postgresql+asyncpg://u:p@host/db?ssl=verify-full&application_name=sevanna"
    )
