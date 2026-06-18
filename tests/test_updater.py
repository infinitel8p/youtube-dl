"""Tests for the pure parts of the updater (version compare + asset selection)."""

from __future__ import annotations

from yt_downloader.updater import is_newer, parse_version, pick_asset


def test_is_newer_handles_v_prefix():
    assert is_newer("1.2", "v1.3") is True
    assert is_newer("v1.3", "1.3") is False
    assert is_newer("2.0.0", "1.9.9") is False


def test_is_newer_with_unparseable_version_is_false():
    assert is_newer("not-a-version", "1.0") is False
    assert is_newer("1.0", "garbage") is False


def test_parse_version_strips_prefix():
    assert parse_version("v1.3") == parse_version("1.3")
    assert parse_version("bad") is None


def test_pick_asset_matches_platform_substring():
    assets = [
        {"name": "YouTube.Downloader.Windows.zip", "browser_download_url": "win"},
        {"name": "YouTube.Downloader.Darwin.zip", "browser_download_url": "mac"},
    ]
    assert pick_asset(assets, "Darwin") == "mac"
    assert pick_asset(assets, "Windows") == "win"
    assert pick_asset(assets, "Linux") is None
