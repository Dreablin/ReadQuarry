from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs"])

_LOG_LOCK = Lock()
_LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=500)
_HANDLER: logging.Handler | None = None


class RingBufferHandler(logging.Handler):
    """Append formatted log records to an in-memory deque for the log viewer API."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            entry = {
                "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": msg,
            }
            with _LOG_LOCK:
                _LOG_BUFFER.append(entry)
        except Exception:
            self.handleError(record)


def install_memory_log_handler() -> None:
    """Attach ring-buffer handler to the root logger (idempotent)."""
    global _HANDLER
    if _HANDLER is not None:
        return
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    h = RingBufferHandler()
    h.setLevel(logging.DEBUG)
    h.setFormatter(fmt)
    root = logging.getLogger()
    root.addHandler(h)
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)
    _HANDLER = h
    logger.debug("Memory log handler installed for /api/logs viewer")


@router.get("")
def get_logs() -> dict[str, Any]:
    """Return recent log entries from the in-memory ring buffer (newest last)."""
    with _LOG_LOCK:
        return {"entries": list(_LOG_BUFFER)}
