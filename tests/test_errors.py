"""Tests for the pure failure classifier."""

from __future__ import annotations

import pytest

from yt_downloader.errors import classify_failure


@pytest.mark.parametrize(
    "text, expected",
    [
        ("ERROR: Sign in to confirm your age", "Video is age-restricted"),
        ("This video is private", "Video is private"),
        ("Join this channel to get access to members-only content", "Members-only video"),
        ("ERROR: Video unavailable", "Video is unavailable or removed"),
        ("This video has been removed by the uploader", "Video is unavailable or removed"),
        ("not made this video available in your country", "Video is blocked in your region"),
        ("This video is DRM protected", "Video is DRM-protected and can't be downloaded"),
        ("ERROR: Unsupported URL: https://example.com/x", "This URL isn't supported"),
        ("ffmpeg not found", "ffmpeg is missing or post-processing failed"),
        ("OSError: [Errno 28] No space left on device", "Your disk is full"),
        ("[Errno 13] Permission denied: '/root/x'", "Permission denied writing to that folder"),
        ("Requested format is not available", "The requested format or quality isn't available"),
    ],
)
def test_classifies_common_failures(text, expected):
    assert classify_failure(text).reason == expected


@pytest.mark.parametrize(
    "text",
    [
        "ERROR: Unable to download webpage: <urlopen error [Errno -2] Name or service not known>",
        "ERROR: Unable to download webpage (caused by ConnectionResetError)",
        "ERROR: read timed out",
    ],
)
def test_network_failures(text):
    assert classify_failure(text).reason == "No internet connection or the site is unreachable"


@pytest.mark.parametrize(
    "text",
    [
        "ERROR: Unable to extract video data; please report this issue on https://github.com/yt-dlp",
        "WARNING: Some formats may be missing",
        "nsig extraction failed: Some formats may be missing",
    ],
)
def test_extraction_failures_flag_stale_ytdlp(text):
    failure = classify_failure(text)
    assert failure.stale_ytdlp is True
    assert failure.hint is not None


def test_empty_and_unknown_fall_back():
    fallback = "Download failed - see the activity log for details."
    assert classify_failure("").reason == fallback
    assert classify_failure(None).reason == fallback
    assert classify_failure("something totally unexpected").reason == fallback


def test_first_match_wins_for_overlapping_text():
    # "private" is more specific than the generic extraction signal that also appears
    text = "ERROR: This video is private. Unable to extract player response"
    assert classify_failure(text).reason == "Video is private"
