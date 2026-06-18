"""Checks GitHub releases and self-updates the frozen app.

The check/compare/pick parts are pure and tested. Actually swapping the binary only
happens in a frozen build; in dev we just point the user at the releases page.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass

import requests
from packaging.version import InvalidVersion, Version

logger = logging.getLogger("yt_downloader")

REPO = "infinitel8p/youtube-dl"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
APP_NAME = "YouTube Downloader"


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    latest: str
    download_url: str | None  # None if no asset matches this platform


def parse_version(text: str) -> Version | None:
    try:
        return Version(text.strip().lstrip("vV"))
    except (InvalidVersion, AttributeError):
        return None


def is_newer(current: str, latest: str) -> bool:
    current_version, latest_version = parse_version(current), parse_version(latest)
    if current_version is None or latest_version is None:
        return False
    return latest_version > current_version


def pick_asset(assets: list[dict], platform_key: str) -> str | None:
    """Pick the download URL whose asset name mentions this platform (e.g. Darwin)."""
    for asset in assets:
        if platform_key.lower() in asset.get("name", "").lower():
            return asset.get("browser_download_url")
    return None


def check_for_update(current_version: str) -> UpdateInfo | None:
    """Return info about a newer release, or None if up to date / check failed."""
    try:
        response = requests.get(
            RELEASES_API, timeout=10, headers={"Accept": "application/vnd.github+json"}
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.error(f"[Update] Could not check for updates: {error}")
        return None

    latest = (data.get("tag_name") or "").strip().lstrip("vV")
    if not latest or not is_newer(current_version, latest):
        logger.info(f"[Update] Up to date (v{current_version}).")
        return None

    download_url = pick_asset(data.get("assets", []), platform.system())
    return UpdateInfo(current=current_version, latest=latest, download_url=download_url)


def download_asset(url: str, dest_path: str, progress_cb=None) -> None:
    """Download url to dest_path, calling progress_cb(downloaded, total) as it goes."""
    with requests.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)
        downloaded = 0
        with open(dest_path, "wb") as out:
            for chunk in response.iter_content(chunk_size=1 << 16):
                out.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)


def can_self_update() -> bool:
    """Self-replace only makes sense in a frozen build with a real executable to swap."""
    return bool(getattr(sys, "frozen", False))


def update_dir(latest: str) -> str:
    path = os.path.join(tempfile.gettempdir(), APP_NAME, "Updates", f"v{latest}")
    os.makedirs(path, exist_ok=True)
    return path


def apply_update(zip_path: str) -> None:
    """Hand off to a detached helper that swaps the app and relaunches it.

    The caller should exit right after so the old binary is free to be replaced.
    """
    system = platform.system()
    if system == "Windows":
        _apply_windows(zip_path)
    elif system == "Darwin":
        _apply_macos(zip_path)
    else:
        raise RuntimeError(f"Self-update is not supported on {system}.")


def _macos_app_path() -> str:
    # sys.executable is .../YouTube Downloader.app/Contents/MacOS/YouTube Downloader
    parts = sys.executable.split(os.sep)
    for index in range(len(parts) - 1, -1, -1):
        if parts[index].endswith(".app"):
            return os.sep.join(parts[: index + 1])
    raise RuntimeError("Could not locate the .app bundle to update.")


def _apply_macos(zip_path: str) -> None:
    app_path = _macos_app_path()
    install_dir = os.path.dirname(app_path)
    log_file = os.path.join(os.path.dirname(zip_path), "update_log.txt")
    script = os.path.join(os.path.dirname(zip_path), "updater.sh")
    with open(script, "w") as out:
        out.write(
            "#!/bin/bash\n"
            f'log="{log_file}"\n'
            'echo "Closing app..." | tee -a "$log"\n'
            f"osascript -e 'quit app \"{APP_NAME}\"' >> \"$log\" 2>&1\n"
            "sleep 2\n"
            f'rm -rf "{app_path}" >> "$log" 2>&1\n'
            f'unzip -o "{zip_path}" -d "{install_dir}" >> "$log" 2>&1\n'
            f'open "{app_path}" >> "$log" 2>&1\n'
            'echo "Done." | tee -a "$log"\n'
        )
    os.chmod(script, 0o755)
    subprocess.Popen(["/bin/bash", script], start_new_session=True)


def _apply_windows(zip_path: str) -> None:
    install_dir = os.path.dirname(sys.executable)
    log_file = os.path.join(os.path.dirname(zip_path), "update_log.txt")
    script = os.path.join(os.path.dirname(zip_path), "updater.ps1")
    with open(script, "w") as out:
        out.write(
            f'$log = "{log_file}"\n'
            f'taskkill /F /IM "{APP_NAME}.exe" /T >> $log 2>&1\n'
            "Start-Sleep -Seconds 2\n"
            f'Expand-Archive -Path "{zip_path}" -DestinationPath "{install_dir}" '
            "-Force >> $log 2>&1\n"
            f'Start-Process "{sys.executable}"\n'
        )
    subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", script],
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )
