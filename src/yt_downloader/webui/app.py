"""Boots the webview window and forwards core events to the frontend.

Replaces the customtkinter main loop. The cross-thread rule becomes simpler here: Python
never touches the DOM, it only emits JSON-serializable events; the Svelte app owns all
rendering. Worker threads keep pushing `events.py` dataclasses onto the queue; a forwarder
thread drains them and calls ``window.__ytdlEvent(...)`` once the page is loaded.
"""

from __future__ import annotations

import json
import logging
import queue
import threading

import webview

from .. import __version__
from ..events import Event
from ..resources import resource_path, use_bundled_binaries
from .api import JsApi
from .log_handler import QueueLogHandler
from .serialization import event_to_dict

logger = logging.getLogger("yt_downloader")

_WINDOW_TITLE = "YouTube Downloader"


def _frontend_entry() -> str:
    """Path to the built frontend's index.html (resolved in dev and when frozen)."""
    return resource_path("web", "dist", "index.html")


class _EventForwarder:
    """Drains the event queue and pushes each event to JS, once the page is ready."""

    def __init__(self, events: queue.Queue[Event], window: webview.Window) -> None:
        self._events = events
        self._window = window
        self._ready = threading.Event()
        self._stop = threading.Event()

    def mark_ready(self) -> None:
        self._ready.set()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        self._ready.wait()
        while not self._stop.is_set():
            try:
                event = self._events.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                payload = json.dumps(event_to_dict(event))
                self._window.evaluate_js(f"window.__ytdlEvent({payload})")
            except Exception:  # noqa: BLE001 - a dead window or bad event must not kill the loop
                if self._stop.is_set():
                    return


def _configure_logging(events: queue.Queue[Event]) -> None:
    logger.setLevel(logging.DEBUG)
    logger.addHandler(QueueLogHandler(events))


def main() -> None:
    """Launch the GUI."""
    use_bundled_binaries()  # put bundled ffmpeg/ffprobe/deno on PATH for yt-dlp
    events: queue.Queue[Event] = queue.Queue()
    _configure_logging(events)

    api = JsApi(events)
    window = webview.create_window(
        _WINDOW_TITLE,
        url=_frontend_entry(),
        js_api=api,
        width=520,
        height=720,
        min_size=(460, 620),
    )
    assert window is not None  # create_window only returns None for an invalid second window
    api.attach_window(window)

    forwarder = _EventForwarder(events, window)
    window.events.loaded += forwarder.mark_ready
    window.events.closed += forwarder.stop
    threading.Thread(target=forwarder.run, daemon=True).start()

    logger.info(f"YouTube Downloader v{__version__} ready.")
    # http_server serves the dist directory so Astro's absolute asset URLs resolve.
    webview.start(http_server=True)


if __name__ == "__main__":
    main()
