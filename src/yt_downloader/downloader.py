"""Runs yt-dlp on a worker thread and reports back through the event queue."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .events import Event, Failed, Finished, Progress, Stage
from .options import build_ydl_options
from .resources import ffmpeg_path

logger = logging.getLogger("yt_downloader")

# Map yt-dlp's internal chatter to friendly status-line text.
_STAGE_KEYWORDS = (
    ("Extracting URL", "Analyzing..."),
    ("[ExtractAudio]", "Extracting audio..."),
    ("[Merger]", "Merging..."),
    ("[VideoRemuxer]", "Finalizing..."),
    ("[VideoConvertor]", "Converting..."),
    ("[EmbedSubtitle]", "Embedding subtitles..."),
)


class _YTDLLogger:
    """Adapts yt-dlp's logger onto our app logger, and turns key lines into stages."""

    def __init__(self, events: queue.Queue[Event]) -> None:
        self._events = events

    def _maybe_stage(self, msg: str) -> None:
        for keyword, stage in _STAGE_KEYWORDS:
            if keyword in msg:
                self._events.put(Stage(stage))
                return

    def info(self, msg: str) -> None:
        logger.info(msg)
        self._maybe_stage(msg)

    def debug(self, msg: str) -> None:
        # yt-dlp is very chatty with per-chunk "[download]" lines on debug
        if "[download]" not in msg:
            logger.debug(msg)
        self._maybe_stage(msg)

    def warning(self, msg: str) -> None:
        logger.warning(msg)

    def error(self, msg: str) -> None:
        logger.error(msg)


def fetch_title(url: str) -> str:
    """Look up a video/playlist title to prefill the save dialog. Does network I/O."""
    logger.info(f"[Analyzing] Fetching video title: {url}\nThis could take a few seconds!")
    options = {"extract_flat": True, "playlist_items": "1", "quiet": True, "no_color": True}
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as error:
        logger.error(f"[Error] Could not fetch video title: {error}")
        return "Download"

    if not info:
        return "Download"
    entries = info.get("entries")
    if entries:
        first = entries[0] or {}
        return first.get("title", "Download")
    return info.get("title", "Download")


@dataclass(frozen=True)
class Metadata:
    """The bits we show on the preview card before a download."""

    title: str
    uploader: str | None = None
    duration: int | None = None  # seconds
    thumbnail_url: str | None = None


def format_duration(seconds: int | None) -> str:
    """Render a duration as M:SS or H:MM:SS. Empty string for unknown/zero."""
    if not seconds or seconds < 0:
        return ""
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _thumbnail_area(thumb: dict) -> int:
    return (thumb.get("width") or 0) * (thumb.get("height") or 0)


def _select_thumbnail(info: dict) -> str | None:
    """Pick the highest-resolution thumbnail URL we can find."""
    usable = [thumb for thumb in (info.get("thumbnails") or []) if thumb.get("url")]
    if usable:
        if any(_thumbnail_area(thumb) for thumb in usable):
            return max(usable, key=_thumbnail_area)["url"]
        # no dimensions given: yt-dlp lists thumbnails worst-to-best, so take the last
        return usable[-1]["url"]
    return info.get("thumbnail")


def fetch_metadata(url: str) -> Metadata | None:
    """Look up title/channel/duration/thumbnail for the preview card. Does network I/O."""
    options = {
        "quiet": True,
        "no_color": True,
        "skip_download": True,
        "noplaylist": True,
        "playlist_items": "1",
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as error:
        logger.debug(f"[Preview] Could not fetch metadata: {error}")
        return None
    except Exception as error:  # noqa: BLE001 - a preview lookup must never crash the app
        logger.debug(f"[Preview] Unexpected error fetching metadata: {error}")
        return None

    if not info:
        return None
    entries = info.get("entries")
    if entries:
        info = entries[0] or {}
    if not info:
        return None
    return Metadata(
        title=info.get("title") or "Untitled",
        uploader=info.get("uploader") or info.get("channel"),
        duration=info.get("duration"),
        thumbnail_url=_select_thumbnail(info),
    )


class DownloadManager:
    def __init__(self, events: queue.Queue[Event]) -> None:
        self._events = events
        self._thread: threading.Thread | None = None
        self._announced_download = False

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        *,
        url: str,
        file_format: str,
        download_dir: str,
        filename: str | None,
        quality: str = "best",
        subtitles: bool = False,
    ) -> bool:
        """Kick off a download. Returns False if one is already running."""
        if self.is_running:
            logger.warning("[Warning] A download is already in progress.")
            return False

        self._thread = threading.Thread(
            target=self._run,
            kwargs={
                "url": url,
                "file_format": file_format,
                "download_dir": download_dir,
                "filename": filename,
                "quality": quality,
                "subtitles": subtitles,
            },
            daemon=True,
        )
        self._thread.start()
        return True

    def _progress_hook(self, status: dict) -> None:
        if status.get("status") != "downloading":
            return
        if not self._announced_download:
            self._announced_download = True
            self._events.put(Stage("Downloading..."))
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        downloaded = status.get("downloaded_bytes", 0)
        fraction = min(downloaded / total, 1.0) if total else None
        self._events.put(
            Progress(fraction, speed=status.get("speed"), eta=status.get("eta"))
        )

    def _postprocessor_hook(self, status: dict) -> None:
        # Stage text comes from _YTDLLogger keywords; just log here.
        state = status.get("status")
        name = status.get("postprocessor", "")
        if state == "started":
            logger.info(f"[Status] Postprocessing started: {name}")
        elif state == "finished":
            logger.info(f"[Status] Postprocessing finished: {name}")

    def _run(
        self,
        *,
        url: str,
        file_format: str,
        download_dir: str,
        filename: str | None,
        quality: str,
        subtitles: bool,
    ) -> None:
        logger.info("[Info] Download initiated.")
        self._announced_download = False
        self._events.put(Stage("Preparing..."))
        options = build_ydl_options(
            file_format=file_format,
            download_dir=download_dir,
            filename=filename,
            ffmpeg_location=ffmpeg_path(),
            quality=quality,
            subtitles=subtitles,
            logger=_YTDLLogger(self._events),
            progress_hooks=[self._progress_hook],
            postprocessor_hooks=[self._postprocessor_hook],
        )
        try:
            with YoutubeDL(options) as ydl:
                retcode = ydl.download([url])
        except DownloadError as error:
            logger.error(f"[Error] {error}")
            self._events.put(Failed(str(error)))
            return
        except Exception as error:  # noqa: BLE001 - surface anything unexpected to the UI
            logger.error(f"[Error] Unexpected failure: {error}")
            self._events.put(Failed(str(error)))
            return

        # ignoreerrors swallows extraction failures (e.g. DRM) without raising, so a
        # non-zero code is the only signal that nothing actually downloaded.
        if retcode:
            logger.error("[Error] Download finished with errors - nothing was saved.")
            self._events.put(Failed("Download failed - see the activity log."))
            return

        logger.info("[Info] Download complete.")
        self._events.put(Progress(1.0))
        self._events.put(Finished())
