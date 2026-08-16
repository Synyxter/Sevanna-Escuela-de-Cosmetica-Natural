"""Object storage abstraction for course images and assets.

Images are never stored as binary blobs in PostgreSQL — only a URL/reference is
persisted. This interface allows swapping local storage for S3/Cloudinary later.
"""

from __future__ import annotations

import abc


class StorageProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        """Store an object and return its public URL."""

    @abc.abstractmethod
    async def delete(self, *, key: str) -> None:
        """Delete an object by key."""

    @abc.abstractmethod
    def get_url(self, *, key: str) -> str:
        """Return the public URL for a stored object key."""
