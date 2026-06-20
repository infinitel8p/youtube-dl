"""Builds yt-dlp option dicts. Pure and UI-free so it can be unit-tested."""

from __future__ import annotations

from typing import Any

from .formats import is_audio_format

# audio stream extension that lives natively in a given video container
_NATIVE_AUDIO_EXT = {"mp4": "m4a", "webm": "webm"}


def _video_format(file_format: str, quality: str) -> str:
    """Prefer streams already in the target container so we can mux without re-encoding."""
    height = f"[height<={quality}]" if quality not in ("", "best") else ""
    audio_ext = _NATIVE_AUDIO_EXT.get(file_format)
    if audio_ext:
        return (
            f"bestvideo{height}[ext={file_format}]+bestaudio[ext={audio_ext}]/"
            f"best{height}[ext={file_format}]/"
            f"bestvideo{height}+bestaudio/best{height}/best"
        )
    # mkv/flv/3gp: no native stream ext to prefer - grab best, the remuxer sets the container
    return f"bestvideo{height}+bestaudio/best{height}/best"


def build_ydl_options(
    *,
    file_format: str,
    download_dir: str,
    filename: str | None,
    ffmpeg_location: str | None,
    quality: str = "best",
    subtitles: bool = False,
    cookies_from_browser: str | None = None,
    logger: Any = None,
    progress_hooks: list | None = None,
    postprocessor_hooks: list | None = None,
) -> dict[str, Any]:
    # filename=None means download a whole playlist using the title template.
    # quality "best" lets yt-dlp choose; otherwise it's a max height (video) or kbps (audio).
    # subtitles only applies to video formats (embedded into the container).
    options: dict[str, Any] = {
        "ffmpeg_location": ffmpeg_location,
        "ignoreerrors": True,
        "no_color": True,
        # Let yt-dlp fetch (and cache) the EJS JS-challenge solver so YouTube's "n" signature
        # solves. Without it, deno runs but the challenge fails ("Some formats may be missing")
        # and capped resolutions fall back to whatever is still accessible. Ignored by older
        # yt-dlp that doesn't support remote components.
        "remote_components": ["ejs:github"],
    }
    # Pull the user's logged-in cookies from their browser, which gets past YouTube's
    # "confirm you're not a bot" gate. yt-dlp expects a tuple; the browser name is enough.
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)
    if logger is not None:
        options["logger"] = logger
    if progress_hooks is not None:
        options["progress_hooks"] = progress_hooks
    if postprocessor_hooks is not None:
        options["postprocessor_hooks"] = postprocessor_hooks

    capped = quality not in ("", "best")

    if is_audio_format(file_format):
        options["format"] = "bestaudio/best"
        postprocessor = {"key": "FFmpegExtractAudio", "preferredcodec": file_format}
        if capped:
            postprocessor["preferredquality"] = quality
        options["postprocessors"] = [postprocessor]
    else:
        options["format"] = _video_format(file_format, quality)
        options["merge_output_format"] = file_format
        # remux into the target container (fast, lossless); only re-encodes if the codecs
        # aren't compatible with it - much faster than always converting
        postprocessors: list[dict[str, Any]] = [
            {"key": "FFmpegVideoRemuxer", "preferedformat": file_format}
        ]
        if subtitles:
            options["writesubtitles"] = True
            options["subtitleslangs"] = ["all"]
            postprocessors.append(
                {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False}
            )
        options["postprocessors"] = postprocessors

    if filename is not None:
        options["playlist_items"] = "1"
        options["outtmpl"] = f"{download_dir}/{filename}.%(ext)s"
    else:
        options["outtmpl"] = f"{download_dir}/%(title)s.%(ext)s"

    return options
