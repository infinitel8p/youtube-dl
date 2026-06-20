"""Tests for log output cleanup."""

from __future__ import annotations

from yt_downloader.webui.log_handler import strip_ansi


def test_strip_ansi_removes_color_codes():
    raw = "\x1b[0;31mERROR:\x1b[0m \x1b[0;94mNOT\x1b[0m supported"
    assert strip_ansi(raw) == "ERROR: NOT supported"


def test_strip_ansi_leaves_plain_text_untouched():
    assert strip_ansi("[Info] Download complete.") == "[Info] Download complete."
