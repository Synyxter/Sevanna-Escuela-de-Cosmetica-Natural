"""Factory + cached selector for the configured storage provider."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.integrations.storage.base import StorageProvider
from app.integrations.storage.local import LocalStorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    match settings.storage_provider:
        case "local":
            return LocalStorageProvider()
        case _:  # pragma: no cover
            raise ValueError(f"Unknown storage provider: {settings.storage_provider}")
