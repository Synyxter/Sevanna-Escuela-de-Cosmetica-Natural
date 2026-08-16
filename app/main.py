"""Sevanna API application factory and entrypoint.

Wires together configuration, logging, middleware, CORS, rate limiting, global
exception handling and the versioned router.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging(settings.log_level)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend de Sevanna — academia de cosmética natural.",
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
    )

    # Rate limiting is applied per-route via dependencies (see app/core/rate_limit).

    # --- CORS: only explicitly allowed frontend origins ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # --- Request id + structured access logging ---
    app.add_middleware(RequestContextMiddleware)

    # --- Global error handling (safe envelopes) ---
    register_exception_handlers(app)

    # --- Routes ---
    app.include_router(api_router)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "ok", "docs": settings.docs_url or ""}

    return app


app = create_app()
