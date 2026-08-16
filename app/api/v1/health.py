from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DBSession

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(session: DBSession) -> dict[str, str]:
    """Readiness probe — verifies the database is reachable."""
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
