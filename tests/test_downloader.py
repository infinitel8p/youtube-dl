"""Tests for the pure metadata/preview helpers in downloader.py."""

from __future__ import annotations

from yt_downloader.downloader import _available_heights, _select_thumbnail, format_duration


def test_available_heights_dedupes_and_sorts_desc():
    info = {
        "formats": [
            {"height": 720, "vcodec": "avc1"},
            {"height": 1080, "vcodec": "vp9"},
            {"height": 720, "vcodec": "vp9"},  # duplicate resolution, different codec
            {"height": 240, "vcodec": "none", "acodec": "mp4a"},  # audio-only, ignored
            {"vcodec": "none", "acodec": "mp4a"},  # audio-only, no height
        ]
    }
    assert _available_heights(info) == (1080, 720)


def test_available_heights_empty_without_video():
    assert _available_heights({}) == ()
    assert _available_heights({"formats": [{"vcodec": "none", "acodec": "mp4a"}]}) == ()


def test_format_duration_minutes():
    assert format_duration(225) == "3:45"


def test_format_duration_pads_seconds():
    assert format_duration(65) == "1:05"


def test_format_duration_hours():
    assert format_duration(3723) == "1:02:03"


def test_format_duration_unknown_is_blank():
    assert format_duration(None) == ""
    assert format_duration(0) == ""
    assert format_duration(-5) == ""


def test_select_thumbnail_prefers_largest_known_dimensions():
    info = {
        "thumbnails": [
            {"url": "small", "width": 120, "height": 90},
            {"url": "big", "width": 1280, "height": 720},
            {"url": "medium", "width": 640, "height": 480},
        ]
    }
    assert _select_thumbnail(info) == "big"


def test_select_thumbnail_falls_back_to_list_order_without_dimensions():
    info = {"thumbnails": [{"url": "first"}, {"url": "last"}]}
    assert _select_thumbnail(info) == "last"


def test_select_thumbnail_uses_single_thumbnail_field():
    assert _select_thumbnail({"thumbnail": "only"}) == "only"


def test_select_thumbnail_returns_none_when_absent():
    assert _select_thumbnail({}) is None
    assert _select_thumbnail({"thumbnails": [{"width": 100}]}) is None
