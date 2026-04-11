from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs"])


def log_with_tag(lgr: logging.Logger, level: int, tag: str, msg: str, *args: Any) -> None:
    """Log a line with a ring-buffer ``tag`` (e.g. ``TIME``, ``LLM``) for the logs API."""
    lgr.log(level, msg, *args, extra={"tag": tag})

_LOG_LOCK = Lock()
_LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=500)
_LOG_APPEND_SEQ: int = 0
_HANDLER: logging.Handler | None = None


class RingBufferHandler(logging.Handler):
    """Append formatted log records to an in-memory deque for the log viewer API."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            tag = getattr(record, "tag", "INFO")
            entry = {
                "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": msg,
                "tag": tag,
            }
            global _LOG_APPEND_SEQ
            with _LOG_LOCK:
                _LOG_APPEND_SEQ += 1
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
    """Return recent log entries from the in-memory ring buffer (newest last).

    ``count`` is the total number of log lines appended (monotonic). It may exceed
    ``len(entries)`` when the ring buffer drops older rows, so clients can detect
    new output without comparing full entry lists (BUGS.md B01).

    Each entry includes a ``tag`` (default ``INFO``). ``tags`` lists distinct tags
    in the buffer, sorted (BUGS.md B04).
    """
    with _LOG_LOCK:
        entries: list[dict[str, Any]] = []
        tag_set: set[str] = set()
        for row in _LOG_BUFFER:
            e = dict(row)
            t = str(e.setdefault("tag", "INFO"))
            e["tag"] = t
            tag_set.add(t)
            entries.append(e)
        return {
            "entries": entries,
            "count": _LOG_APPEND_SEQ,
            "tags": sorted(tag_set),
        }
