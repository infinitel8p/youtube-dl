"""Events passed from worker threads to the UI thread via a queue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LogLevel = Literal["debug", "info", "warning", "error"]


@dataclass(frozen=True)
class LogMessage:
    text: str
    level: LogLevel = "info"


@dataclass(frozen=True)
class Stage:
    """A status-line update like "Downloading..."."""

    text: str


@dataclass(frozen=True)
class Progress:
    # fraction is None when the total size is unknown (UI shows an indeterminate bar)
    fraction: float | None
    speed: float | None = None  # bytes/s
    eta: int | None = None  # seconds


@dataclass(frozen=True)
class Finished:
    pass


@dataclass(frozen=True)
class Failed:
    message: str


Event = LogMessage | Stage | Progress | Finished | Failed
