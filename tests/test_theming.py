"""Tests for the bundled theme registry."""

from __future__ import annotations

import os

from yt_downloader.theming import DEFAULT_THEME, available_themes, theme_path


def test_default_theme_is_available():
    stems = [stem for _, stem in available_themes()]
    assert DEFAULT_THEME in stems


def test_default_theme_is_listed_first():
    assert available_themes()[0][1] == DEFAULT_THEME


def test_every_theme_file_exists():
    for _, stem in available_themes():
        assert os.path.exists(theme_path(stem))


def test_display_names_are_unique():
    labels = [label for label, _ in available_themes()]
    assert len(labels) == len(set(labels))


def test_typo_stem_gets_a_clean_display_name():
    by_stem = {stem: label for label, stem in available_themes()}
    if "prurple" in by_stem:
        assert by_stem["prurple"] == "Purple"
