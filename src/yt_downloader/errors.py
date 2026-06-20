"""Classifies yt-dlp / download failures into short, friendly reasons.

Pure and UI-free so it's easy to unit-test. The full technical error still goes to the
activity log; ``classify_failure`` only produces the short reason shown in the status line
plus an optional actionable hint. ``stale_ytdlp`` flags the "extraction broke" failures that
usually mean yt-dlp needs an update.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_UPDATE_HINT = "yt-dlp may be out of date - try updating it."
_FALLBACK = "Download failed - see the activity log for details."


@dataclass(frozen=True)
class Failure:
    reason: str  # short, status-line friendly
    hint: str | None = None  # optional actionable suggestion (logged as a warning)
    stale_ytdlp: bool = False  # extraction failed - likely needs a yt-dlp update


# Ordered (compiled pattern, reason, hint, stale). First match wins, so the more specific
# patterns come before the broad network/extraction ones.
_PATTERNS: tuple[tuple[re.Pattern[str], str, str | None, bool], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), reason, hint, stale)
    for pattern, reason, hint, stale in (
        (
            r"confirm you'?re not a bot|not a bot",
            "YouTube is asking to confirm you're not a bot",
            "This usually needs sign-in cookies; updating yt-dlp often helps too.",
            False,
        ),
        (
            r"confirm your age|age[- ]?restricted|inappropriate for some users",
            "Video is age-restricted",
            None,
            False,
        ),
        (r"private video|this video is private", "Video is private", None, False),
        (
            r"members[- ]?only|join this channel|available to this channel's members",
            "Members-only video",
            None,
            False,
        ),
        (
            r"video unavailable|has been removed|no longer available|been terminated"
            r"|removed by the uploader|this video is not available",
            "Video is unavailable or removed",
            None,
            False,
        ),
        (
            r"available in your country|geo[- ]?restricted|blocked it in your country"
            r"|not available from your location|available in your location",
            "Video is blocked in your region",
            None,
            False,
        ),
        (
            r"\bdrm\b|protected by drm",
            "Video is DRM-protected and can't be downloaded",
            None,
            False,
        ),
        (
            r"premieres in|this live event will begin|live event will begin in",
            "This is a scheduled premiere/live that hasn't started yet",
            None,
            False,
        ),
        (
            r"requested format is not available|requested format not available",
            "The requested format or quality isn't available",
            "Try 'Best available' or a different format.",
            False,
        ),
        (
            r"no space left|errno 28|not enough space|disk full",
            "Your disk is full",
            None,
            False,
        ),
        (
            r"permission denied|errno 13|access is denied|operation not permitted",
            "Permission denied writing to that folder",
            "Pick a different output folder.",
            False,
        ),
        (
            r"ffmpeg not found|ffmpeg is not installed|ffprobe and ffmpeg not found"
            r"|requested merging.*but ffmpeg|postprocessing:|conversion failed"
            r"|postprocessor",
            "ffmpeg is missing or post-processing failed",
            None,
            False,
        ),
        (
            r"unable to download webpage|getaddrinfo|failed to resolve|name or service not known"
            r"|temporary failure in name resolution|connection refused|connection reset"
            r"|connection aborted|timed out|timeout|network is unreachable|urlopen error"
            r"|errno -2|errno -3|max retries exceeded|read timed out",
            "No internet connection or the site is unreachable",
            None,
            False,
        ),
        (
            r"unsupported url|is not a valid url",
            "This URL isn't supported",
            None,
            False,
        ),
        (
            r"unable to extract|failed to extract|nsig extraction failed"
            r"|some formats may be missing|signature extraction failed"
            r"|unable to extract yt initial data|player response"
            r"|could not find|fragment.*not found",
            "yt-dlp couldn't read this page",
            _UPDATE_HINT,
            True,
        ),
    )
)


def classify_failure(text: str | None) -> Failure:
    """Map a yt-dlp/download error string to a short, friendly Failure."""
    message = (text or "").strip()
    if not message:
        return Failure(reason=_FALLBACK)
    for pattern, reason, hint, stale in _PATTERNS:
        if pattern.search(message):
            return Failure(reason=reason, hint=hint, stale_ytdlp=stale)
    return Failure(reason=_FALLBACK)
