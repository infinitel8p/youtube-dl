"""Output formats and quality options - the single source of truth for both."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputFormat:
    extension: str
    is_audio: bool


# Order here is the order shown in the UI dropdown.
OUTPUT_FORMATS: tuple[OutputFormat, ...] = (
    OutputFormat("mp4", is_audio=False),
    OutputFormat("mp3", is_audio=True),
    OutputFormat("m4a", is_audio=True),
    OutputFormat("flac", is_audio=True),
    OutputFormat("aac", is_audio=True),
    OutputFormat("wav", is_audio=True),
    OutputFormat("ogg", is_audio=True),
    OutputFormat("flv", is_audio=False),
    OutputFormat("3gp", is_audio=False),
    OutputFormat("webm", is_audio=False),
    OutputFormat("mkv", is_audio=False),
)

DEFAULT_FORMAT = "mp4"

# (label, token). "best" lets yt-dlp pick; video tokens are a max height, audio are kbps.
VIDEO_QUALITIES: tuple[tuple[str, str], ...] = (
    ("Best available", "best"),
    ("2160p (4K)", "2160"),
    ("1440p (2K)", "1440"),
    ("1080p", "1080"),
    ("720p", "720"),
    ("480p", "480"),
    ("360p", "360"),
)

AUDIO_QUALITIES: tuple[tuple[str, str], ...] = (
    ("Best available", "best"),
    ("320 kbps", "320"),
    ("256 kbps", "256"),
    ("192 kbps", "192"),
    ("128 kbps", "128"),
)

DEFAULT_QUALITY = "best"

_BY_EXTENSION = {output_format.extension: output_format for output_format in OUTPUT_FORMATS}


def extensions() -> list[str]:
    return [output_format.extension for output_format in OUTPUT_FORMATS]


def is_audio_format(extension: str) -> bool:
    return _BY_EXTENSION[extension].is_audio


def quality_choices(extension: str) -> tuple[tuple[str, str], ...]:
    return AUDIO_QUALITIES if is_audio_format(extension) else VIDEO_QUALITIES
