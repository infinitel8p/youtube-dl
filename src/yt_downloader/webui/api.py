"""The JS bridge: methods the frontend calls via ``window.pywebview.api.*``.

Each method runs on a pywebview-managed thread (off the UI thread), so blocking work
(metadata lookups, file dialogs, update downloads) is fine here. Results come back to JS
as resolved Promises; ongoing download/update progress is delivered separately as events
pushed onto the queue and forwarded to ``window.__ytdlEvent`` (see app.py).
"""

from __future__ import annotations

import dataclasses
import logging
import os
import queue
import subprocess
import sys
import threading
import webbrowser

import webview

from .. import __version__, updater, ytdlp
from ..downloader import DownloadManager, fetch_metadata
from ..events import Event, LogMessage
from ..formats import DEFAULT_FORMAT, OUTPUT_FORMATS, quality_choices

logger = logging.getLogger("yt_downloader")


class JsApi:
    """Everything the frontend can invoke. Holds the download manager and event queue."""

    def __init__(self, events: queue.Queue[Event]) -> None:
        self._events = events
        self._manager = DownloadManager(events)
        self._window: webview.Window | None = None

    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    # -- catalog -------------------------------------------------------------

    def get_app_info(self) -> dict:
        return {"version": __version__, "canSelfUpdate": updater.can_self_update()}

    def list_formats(self) -> dict:
        """The selectable output formats and their per-format quality choices."""
        return {
            "default": DEFAULT_FORMAT,
            "formats": [
                {
                    "extension": output_format.extension,
                    "isAudio": output_format.is_audio,
                    "qualities": [
                        {"label": label, "token": token}
                        for label, token in quality_choices(output_format.extension)
                    ],
                }
                for output_format in OUTPUT_FORMATS
            ],
        }

    # -- preview -------------------------------------------------------------

    def fetch_metadata(self, url: str, cookies_from_browser: str | None = None) -> dict | None:
        """Title/channel/duration/thumbnail for the preview card, or None on failure."""
        metadata = fetch_metadata(url, cookies_from_browser or None)
        return dataclasses.asdict(metadata) if metadata is not None else None

    # -- download ------------------------------------------------------------

    def choose_save_path(self, suggested_name: str, extension: str) -> str | None:
        """Native save dialog for a single download. Returns the chosen path or None."""
        name = (suggested_name or "").strip() or "video"
        result = self._require_window().create_file_dialog(
            _dialog("SAVE"),
            save_filename=f"{name}.{extension}",
            file_types=(f"{extension.upper()} file (*.{extension})", "All files (*.*)"),
        )
        return _single_path(result)

    def choose_folder(self) -> str | None:
        """Native folder dialog for a playlist download. Returns the path or None."""
        result = self._require_window().create_file_dialog(_dialog("FOLDER"))
        return _single_path(result)

    def _require_window(self) -> webview.Window:
        if self._window is None:
            raise RuntimeError("Window not attached yet.")
        return self._window

    def start_download(self, request: dict) -> bool:
        """Begin a download. ``request`` carries url/format/quality/subtitles/target.

        For a playlist, ``target`` is a directory; otherwise it is the full save path.
        Progress, log, finished and failed all arrive later as events.
        """
        url = (request.get("url") or "").strip()
        target = request.get("target") or ""
        if not url or not target:
            logger.warning("[Warning] Missing URL or destination.")
            return False

        is_playlist = bool(request.get("playlist"))
        if is_playlist:
            download_dir, filename = target, None
        else:
            download_dir, name_with_ext = os.path.split(target)
            filename = os.path.splitext(name_with_ext)[0]

        return self._manager.start(
            url=url,
            file_format=request.get("format", DEFAULT_FORMAT),
            download_dir=download_dir,
            filename=filename,
            quality=request.get("quality", "best"),
            subtitles=bool(request.get("subtitles")),
            cookies_from_browser=(request.get("cookiesFromBrowser") or None),
        )

    def cancel_download(self) -> bool:
        """Ask the running download to stop. Returns False if nothing is running."""
        return self._manager.cancel()

    def read_clipboard(self) -> str:
        """Return the OS clipboard text, or "" if it's empty/unavailable.

        The webview's ``navigator.clipboard`` is unreliable (often blocked), so the Paste
        button reads the clipboard here instead.
        """
        try:
            import pyperclip

            return pyperclip.paste() or ""
        except Exception as error:  # noqa: BLE001 - clipboard access is best-effort
            logger.debug(f"[Paste] Clipboard read failed: {error}")
            return ""

    def open_folder(self, path: str) -> bool:
        """Open ``path`` in the OS file manager. Returns False on a missing path/failure."""
        if not path or not os.path.isdir(path):
            return False
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            elif sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606 - Windows only
            else:
                subprocess.Popen(["xdg-open", path])
            return True
        except Exception as error:  # noqa: BLE001 - opening a folder must never crash the app
            logger.error(f"[Error] Could not open folder: {error}")
            return False

    # -- updates -------------------------------------------------------------

    def check_update(self) -> dict | None:
        info = updater.check_for_update(__version__)
        if info is None:
            return None
        return {
            "current": info.current,
            "latest": info.latest,
            "downloadUrl": info.download_url,
            "canSelfUpdate": updater.can_self_update(),
        }

    def apply_update(self, latest: str, download_url: str | None) -> dict:
        """Either self-update (frozen build with a matching asset) or open the page."""
        if not download_url or not updater.can_self_update():
            webbrowser.open(updater.RELEASES_PAGE)
            return {"action": "openedReleases"}
        threading.Thread(
            target=self._download_and_apply, args=(latest, download_url), daemon=True
        ).start()
        return {"action": "downloading"}

    def open_releases_page(self) -> None:
        webbrowser.open(updater.RELEASES_PAGE)

    # -- yt-dlp version ------------------------------------------------------

    def check_ytdlp(self) -> dict:
        """Report the installed yt-dlp version and whether a newer one is on PyPI."""
        installed = ytdlp.installed_version()
        latest = ytdlp.latest_version()
        return {
            "installed": installed,
            "latest": latest,
            "outdated": ytdlp.is_outdated(installed, latest),
            "canUpdate": ytdlp.can_pip_update(),
        }

    def update_ytdlp(self) -> dict:
        """pip-upgrade yt-dlp off-thread (dev installs only). Progress arrives as log events."""
        if not ytdlp.can_pip_update():
            logger.warning(
                "[yt-dlp] Bundled builds can't update yt-dlp on their own - update the app instead."
            )
            return {"action": "unsupported"}
        threading.Thread(target=self._run_ytdlp_update, daemon=True).start()
        return {"action": "updating"}

    def _run_ytdlp_update(self) -> None:
        logger.info("[yt-dlp] Updating yt-dlp...")
        succeeded, detail = ytdlp.update_via_pip()
        if succeeded:
            logger.info("[yt-dlp] Updated. Restart the app to use the new version.")
        else:
            logger.error(f"[yt-dlp] Update failed: {detail}")

    def _download_and_apply(self, latest: str, download_url: str) -> None:
        try:
            dest = os.path.join(updater.update_dir(latest), f"{updater.APP_NAME}.zip")
            updater.download_asset(
                download_url,
                dest,
                progress_cb=lambda done, total: self._events.put(
                    LogMessage(f"[Update] Downloading {_mb(done)} / {_mb(total)} MB", "info")
                ),
            )
            updater.apply_update(dest)
            if self._window is not None:
                self._window.destroy()
        except Exception as error:  # noqa: BLE001 - surface any failure, fall back to the page
            logger.error(f"[Update] Update failed: {error}")
            webbrowser.open(updater.RELEASES_PAGE)


def _dialog(kind: str):
    """pywebview 6 uses the FileDialog enum; older versions use the *_DIALOG constants."""
    file_dialog = getattr(webview, "FileDialog", None)
    if file_dialog is not None:
        return getattr(file_dialog, kind)
    return getattr(webview, f"{kind}_DIALOG")


def _single_path(result) -> str | None:
    """pywebview returns a string (save) or a tuple/list (open/folder); normalize it."""
    if not result:
        return None
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    return result


def _mb(num_bytes: int) -> str:
    return f"{num_bytes / 1024 / 1024:.1f}"
