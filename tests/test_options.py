"""Tests for the pure yt-dlp option builder."""

from __future__ import annotations

import pytest

from yt_downloader.options import build_ydl_options


def _audio_options(file_format: str):
    return build_ydl_options(
        file_format=file_format,
        download_dir="/tmp/out",
        filename="song",
        ffmpeg_location="/usr/bin/ffmpeg",
    )


def test_enables_ejs_remote_component_for_youtube_challenges():
    # required so yt-dlp can solve YouTube's "n" JS challenge and expose all formats
    assert _audio_options("mp3")["remote_components"] == ["ejs:github"]


def test_cookies_from_browser_sets_option_as_tuple():
    options = build_ydl_options(
        file_format="mp4",
        download_dir="/tmp/out",
        filename="v",
        ffmpeg_location=None,
        cookies_from_browser="chrome",
    )
    assert options["cookiesfrombrowser"] == ("chrome",)


def test_no_cookies_option_by_default():
    assert "cookiesfrombrowser" not in _audio_options("mp3")


def test_audio_format_uses_extract_audio_postprocessor():
    options = _audio_options("mp3")
    assert options["format"] == "bestaudio/best"
    assert options["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
    ]


def test_video_prefers_target_container_and_remuxes():
    options = build_ydl_options(
        file_format="mp4",
        download_dir="/tmp/out",
        filename="clip",
        ffmpeg_location="/usr/bin/ffmpeg",
    )
    # prefer mp4 streams so we can mux without re-encoding, fall back to best
    assert "bestvideo[ext=mp4]+bestaudio[ext=m4a]" in options["format"]
    assert options["format"].endswith("/best")
    assert options["merge_output_format"] == "mp4"
    assert options["postprocessors"] == [
        {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}
    ]


def test_single_video_limits_to_one_item_and_uses_filename_template():
    options = build_ydl_options(
        file_format="mp4",
        download_dir="/tmp/out",
        filename="clip",
        ffmpeg_location="/usr/bin/ffmpeg",
    )
    assert options["playlist_items"] == "1"
    assert options["outtmpl"] == "/tmp/out/clip.%(ext)s"


def test_playlist_uses_title_template_and_no_item_limit():
    options = build_ydl_options(
        file_format="mp4",
        download_dir="/tmp/out",
        filename=None,
        ffmpeg_location="/usr/bin/ffmpeg",
    )
    assert "playlist_items" not in options
    assert options["outtmpl"] == "/tmp/out/%(title)s.%(ext)s"


def test_optional_hooks_and_logger_are_omitted_when_not_provided():
    options = _audio_options("wav")
    assert "logger" not in options
    assert "progress_hooks" not in options
    assert "postprocessor_hooks" not in options
    assert options["ignoreerrors"] is True
    assert options["ffmpeg_location"] == "/usr/bin/ffmpeg"


def test_video_quality_caps_height():
    options = build_ydl_options(
        file_format="mp4",
        download_dir="/tmp/out",
        filename="clip",
        ffmpeg_location="/usr/bin/ffmpeg",
        quality="1080",
    )
    assert "[height<=1080]" in options["format"]
    assert "bestvideo[height<=1080][ext=mp4]" in options["format"]


def test_flac_extracts_lossless_audio():
    options = _audio_options("flac")
    assert options["format"] == "bestaudio/best"
    assert options["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "flac"}
    ]
    # audio extraction never sets a video merge container
    assert "merge_output_format" not in options


def test_audio_quality_sets_preferred_bitrate():
    options = build_ydl_options(
        file_format="mp3",
        download_dir="/tmp/out",
        filename="song",
        ffmpeg_location="/usr/bin/ffmpeg",
        quality="192",
    )
    assert options["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
    ]


def test_best_quality_leaves_format_uncapped():
    options = build_ydl_options(
        file_format="mp4",
        download_dir="/tmp/out",
        filename="clip",
        ffmpeg_location="/usr/bin/ffmpeg",
        quality="best",
    )
    assert "height<=" not in options["format"]


def test_subtitles_embed_for_video():
    options = build_ydl_options(
        file_format="mkv",
        download_dir="/tmp/out",
        filename="clip",
        ffmpeg_location="/usr/bin/ffmpeg",
        subtitles=True,
    )
    assert options["writesubtitles"] is True
    assert options["subtitleslangs"] == ["all"]
    assert {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False} in options[
        "postprocessors"
    ]


def test_subtitles_ignored_for_audio():
    options = build_ydl_options(
        file_format="mp3",
        download_dir="/tmp/out",
        filename="song",
        ffmpeg_location="/usr/bin/ffmpeg",
        subtitles=True,
    )
    assert "writesubtitles" not in options


def test_unknown_format_raises():
    with pytest.raises(KeyError):
        _audio_options("xyz")
