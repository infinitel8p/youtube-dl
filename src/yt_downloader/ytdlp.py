"""yt-dlp version checks and (in a dev/pip install) self-update.

yt-dlp breaks often as sites change, so we surface the installed version, check PyPI for a
newer one, and - when running from a normal Python install rather than a frozen build - can
pip-upgrade it. The version helpers are pure and unit-tested; the network/subprocess parts
are kept thin. In a frozen build yt-dlp is bundled and can only be refreshed by updating the
whole app (see updater.py).
"""

from __future__ import annotations

import logging
import subprocess
import sys

import requests
from packaging.version import InvalidVersion, Version

logger = logging.getLogger("yt_downloader")

PYPI_JSON = "https://pypi.org/pypi/yt-dlp/json"


def installed_version() -> str | None:
    """The yt-dlp version bundled/installed right now, or None if it can't be read."""
    try:
        from yt_dlp.version import __version__ as version
    except Exception:  # noqa: BLE001 - never let a version read crash the app
        return None
    return version


def latest_version(timeout: float = 10) -> str | None:
    """The newest yt-dlp version on PyPI, or None if the lookup failed."""
    try:
        response = requests.get(PYPI_JSON, timeout=timeout)
        response.raise_for_status()
        return (response.json().get("info") or {}).get("version")
    except (requests.RequestException, ValueError) as error:
        logger.debug(f"[yt-dlp] Could not check PyPI for updates: {error}")
        return None


def is_outdated(installed: str | None, latest: str | None) -> bool:
    """True only when both versions parse and latest is strictly newer."""
    try:
        return Version(str(latest)) > Version(str(installed))
    except (InvalidVersion, TypeError):
        return False


def can_pip_update() -> bool:
    """A frozen build can't pip-install over its bundled yt-dlp; only a dev install can."""
    return not bool(getattr(sys, "frozen", False))


def update_via_pip(timeout: float = 300) -> tuple[bool, str]:
    """Run ``pip install --upgrade yt-dlp``. Returns (succeeded, detail)."""
    command = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except Exception as error:  # noqa: BLE001 - report any spawn/timeout failure to the caller
        return False, str(error)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "pip exited non-zero").strip()
    return True, (result.stdout or "").strip()
