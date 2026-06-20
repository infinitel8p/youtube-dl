"""Tests for the pure yt-dlp version helpers."""

from __future__ import annotations

from yt_downloader import ytdlp


def test_is_outdated_compares_versions():
    assert ytdlp.is_outdated("2024.01.01", "2024.12.06") is True
    assert ytdlp.is_outdated("2024.12.06", "2024.12.06") is False
    assert ytdlp.is_outdated("2024.12.06", "2024.01.01") is False


def test_is_outdated_handles_missing_or_bad_versions():
    assert ytdlp.is_outdated(None, "2024.12.06") is False
    assert ytdlp.is_outdated("2024.12.06", None) is False
    assert ytdlp.is_outdated("not-a-version", "2024.12.06") is False


def test_installed_version_is_readable():
    # yt-dlp is a hard dependency, so this should always resolve in the test env.
    assert ytdlp.installed_version()
