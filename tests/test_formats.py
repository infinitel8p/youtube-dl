"""Tests for the output format registry."""

from __future__ import annotations

import pytest

from yt_downloader.formats import (
    AUDIO_QUALITIES,
    DEFAULT_FORMAT,
    VIDEO_QUALITIES,
    extensions,
    is_audio_format,
    quality_choices,
)


def test_default_format_is_selectable():
    assert DEFAULT_FORMAT in extensions()


def test_extensions_are_unique():
    available = extensions()
    assert len(available) == len(set(available))


@pytest.mark.parametrize("extension", ["mp3", "m4a", "aac", "wav", "ogg", "flac"])
def test_audio_formats(extension):
    assert is_audio_format(extension) is True


@pytest.mark.parametrize("extension", ["mp4", "flv", "3gp", "webm", "mkv"])
def test_video_formats(extension):
    assert is_audio_format(extension) is False


def test_unknown_extension_raises():
    with pytest.raises(KeyError):
        is_audio_format("nope")


def test_quality_choices_match_format_type():
    assert quality_choices("mp3") == AUDIO_QUALITIES
    assert quality_choices("mp4") == VIDEO_QUALITIES


def test_quality_choices_start_with_best():
    for label, token in (VIDEO_QUALITIES[0], AUDIO_QUALITIES[0]):
        assert token == "best"
        assert "Best" in label
