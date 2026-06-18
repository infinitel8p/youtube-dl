"""The bundled customtkinter colour themes and their display names."""

from __future__ import annotations

import os

from .resources import resource_path

DEFAULT_THEME = "polished"

# Nicely-cased display names for stems that don't title-case well.
_DISPLAY_OVERRIDES = {
    "prurple": "Purple",  # the file name is a typo; show it properly in the UI
}


def _display_name(stem: str) -> str:
    return _DISPLAY_OVERRIDES.get(stem, stem.replace("_", " ").title())


def available_themes() -> list[tuple[str, str]]:
    """(display name, file stem) for every bundled theme: default first, then A-Z."""
    themes_dir = resource_path("themes")
    stems = sorted(
        os.path.splitext(name)[0]
        for name in os.listdir(themes_dir)
        if name.endswith(".json")
    )
    if DEFAULT_THEME in stems:
        stems.remove(DEFAULT_THEME)
        stems.insert(0, DEFAULT_THEME)
    return [(_display_name(stem), stem) for stem in stems]


def theme_path(stem: str) -> str:
    return resource_path("themes", f"{stem}.json")
