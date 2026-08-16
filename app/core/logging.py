"""Structured JSON logging configuration.

Logs are emitted as single-line JSON so they can be ingested by log platforms.
Sensitive values (passwords, tokens, secrets, card data) must never be logged.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach contextual extras injected via `logger.info(..., extra={...})`.
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "event"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Quiet down noisy libraries; keep our own logger verbose.
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("sevanna").setLevel(level.upper())
