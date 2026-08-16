"""Local filesystem storage provider (development default).

Uses versioned/unique object keys so replacing an image never produces broken
references. Swap for an S3/Cloudinary provider in production.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import settings
from app.integrations.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    name = "local"

    def __init__(self) -> None:
        self._root = Path(settings.storage_local_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._base_url = settings.storage_public_base_url.rstrip("/")

    @staticmethod
    def build_key(filename: str) -> str:
        """Generate a unique, collision-free object key preserving the suffix."""
        suffix = Path(filename).suffix
        return f"{uuid.uuid4().hex}{suffix}"

    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        path = self._root / key
        path.write_bytes(content)
        return self.get_url(key=key)

    async def delete(self, *, key: str) -> None:
        path = self._root / key
        if path.exists():
            path.unlink()

    def get_url(self, *, key: str) -> str:
        return f"{self._base_url}/{key}"
