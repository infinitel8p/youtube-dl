"""Logging handler that enqueues records for the UI thread instead of touching widgets."""

from __future__ import annotations

import logging
import queue
import re

from ..events import Event, LogLevel, LogMessage

_LEVEL_NAMES: dict[int, LogLevel] = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warning",
    logging.ERROR: "error",
    logging.CRITICAL: "error",
}

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Drop terminal colour codes that yt-dlp sometimes emits."""
    return _ANSI_RE.sub("", text)


class QueueLogHandler(logging.Handler):
    def __init__(self, events: queue.Queue[Event]) -> None:
        super().__init__()
        self._events = events
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _LEVEL_NAMES.get(record.levelno, "info")
            self._events.put(LogMessage(strip_ansi(self.format(record)), level=level))
        except Exception:  # noqa: BLE001 - logging must never raise
            self.handleError(record)
