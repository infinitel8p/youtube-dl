"""Tests for the pure parts of the JS bridge (no webview/GUI needed)."""

from __future__ import annotations

import queue

from yt_downloader.webui.api import JsApi


def _api() -> JsApi:
    return JsApi(queue.Queue())


class _FakeManager:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def start(self, **kwargs) -> bool:
        self.kwargs = kwargs
        return True


def test_list_formats_shape():
    catalog = _api().list_formats()
    assert catalog["default"] == "mp4"
    extensions = [entry["extension"] for entry in catalog["formats"]]
    assert "mp4" in extensions and "mp3" in extensions
    mp3 = next(entry for entry in catalog["formats"] if entry["extension"] == "mp3")
    assert mp3["isAudio"] is True
    assert mp3["qualities"][0]["token"] == "best"


def test_get_app_info_reports_version():
    info = _api().get_app_info()
    assert info["version"]
    assert "canSelfUpdate" in info


def test_start_download_single_splits_save_path():
    api = _api()
    manager = _FakeManager()
    api._manager = manager  # type: ignore[assignment]
    started = api.start_download(
        {
            "url": "https://example.com/v",
            "target": "/a/b/My Video.mp4",
            "format": "mp4",
            "quality": "720",
            "subtitles": True,
            "playlist": False,
        }
    )
    assert started is True
    assert manager.kwargs is not None
    assert manager.kwargs["download_dir"] == "/a/b"
    assert manager.kwargs["filename"] == "My Video"
    assert manager.kwargs["file_format"] == "mp4"
    assert manager.kwargs["quality"] == "720"
    assert manager.kwargs["subtitles"] is True


def test_start_download_playlist_uses_directory():
    api = _api()
    manager = _FakeManager()
    api._manager = manager  # type: ignore[assignment]
    api.start_download(
        {"url": "https://example.com/p", "target": "/downloads", "playlist": True, "format": "mp4"}
    )
    assert manager.kwargs is not None
    assert manager.kwargs["download_dir"] == "/downloads"
    assert manager.kwargs["filename"] is None


def test_start_download_rejects_missing_input():
    api = _api()
    assert api.start_download({"url": "", "target": "/x"}) is False
    assert api.start_download({"url": "https://x", "target": ""}) is False


def test_cancel_download_returns_false_when_idle():
    assert _api().cancel_download() is False


def test_open_folder_rejects_missing_path():
    api = _api()
    assert api.open_folder("") is False
    assert api.open_folder("/this/path/does/not/exist/at/all") is False
