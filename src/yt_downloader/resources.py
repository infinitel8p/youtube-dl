"""Paths to bundled assets, working in dev and when frozen by PyInstaller."""

from __future__ import annotations

import os
import shutil
import sys


def _base_path() -> str:
    # PyInstaller unpacks bundled data into a temp folder exposed as _MEIPASS
    meipass = getattr(sys, "_MEIPASS", None)
    return meipass if meipass else os.path.abspath(".")


def resource_path(*relative_parts: str) -> str:
    return os.path.join(_base_path(), *relative_parts)


def ffmpeg_path() -> str | None:
    """Prefer the bundled ffmpeg, fall back to one on PATH, else None (yt-dlp searches)."""
    binary = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    bundled = resource_path("ffmpeg-binaries", binary)
    if os.path.exists(bundled):
        return bundled
    return shutil.which("ffmpeg")
