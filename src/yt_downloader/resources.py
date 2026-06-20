"""Paths to bundled assets, working in dev and when frozen by PyInstaller."""

from __future__ import annotations

import os
import shutil
import stat
import sys


def _base_path() -> str:
    # PyInstaller unpacks bundled data into a temp folder exposed as _MEIPASS
    meipass = getattr(sys, "_MEIPASS", None)
    return meipass if meipass else os.path.abspath(".")


def resource_path(*relative_parts: str) -> str:
    return os.path.join(_base_path(), *relative_parts)


# Bundled binaries (ffmpeg, ffprobe, deno) live here. Populated by
# scripts/fetch_binaries.py in dev/CI and bundled into the frozen app.
BUNDLED_BIN_DIR = "ffmpeg-binaries"


def bundled_bin_dir() -> str:
    return resource_path(BUNDLED_BIN_DIR)


def ffmpeg_path() -> str | None:
    """Prefer the bundled ffmpeg, fall back to one on PATH, else None (yt-dlp searches)."""
    binary = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    bundled = os.path.join(bundled_bin_dir(), binary)
    if os.path.exists(bundled):
        return bundled
    return shutil.which("ffmpeg")


def use_bundled_binaries() -> None:
    """Prepend the bundled binary dir to PATH.

    yt-dlp discovers ffmpeg/ffprobe and the deno JavaScript runtime (required for current
    YouTube extraction) from PATH, so this makes a shipped build "just work" without the
    user installing anything. A no-op when the directory isn't present (e.g. binaries not
    fetched yet in dev).
    """
    directory = bundled_bin_dir()
    if not os.path.isdir(directory):
        return
    os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")
    # PyInstaller can drop the executable bit when bundling binaries as data; restore it.
    if not sys.platform.startswith("win"):
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                mode = os.stat(path).st_mode
                os.chmod(path, mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
