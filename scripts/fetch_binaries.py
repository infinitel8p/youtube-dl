"""Download the bundled runtime binaries (ffmpeg + deno) for a platform.

We do NOT commit these (they are large and platform-specific). Run this once after
cloning, and in CI before PyInstaller, so the build can ship binaries that "just work":

    python scripts/fetch_binaries.py            # for the current OS/arch
    python scripts/fetch_binaries.py --target darwin-arm64

They land in `ffmpeg-binaries/` (ffmpeg[.exe], deno[.exe]); at runtime the app prepends
that directory to PATH (see resources.use_bundled_binaries), so yt-dlp finds ffmpeg for
merging/remuxing and deno as the JavaScript runtime YouTube extraction now requires.

ffmpeg comes from eugeneware/ffmpeg-static (per-arch GPL static builds); deno from the
official denoland/deno releases.
"""

from __future__ import annotations

import argparse
import io
import os
import platform
import stat
import sys
import urllib.request
import zipfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST_DIR = os.path.join(_REPO_ROOT, "ffmpeg-binaries")

# target key -> (ffmpeg asset, deno asset). ffmpeg-static assets are raw binaries;
# deno assets are zips containing a single `deno`/`deno.exe`.
_FFMPEG_BASE = "https://github.com/eugeneware/ffmpeg-static/releases/latest/download"
_DENO_BASE = "https://github.com/denoland/deno/releases/latest/download"

_TARGETS = {
    "darwin-arm64": ("ffmpeg-darwin-arm64", "deno-aarch64-apple-darwin.zip"),
    "darwin-x86_64": ("ffmpeg-darwin-x64", "deno-x86_64-apple-darwin.zip"),
    "linux-x86_64": ("ffmpeg-linux-x64", "deno-x86_64-unknown-linux-gnu.zip"),
    "linux-arm64": ("ffmpeg-linux-arm64", "deno-aarch64-unknown-linux-gnu.zip"),
    "windows-x86_64": ("ffmpeg-win32-x64", "deno-x86_64-pc-windows-msvc.zip"),
}

_ARCH_ALIASES = {
    "aarch64": "arm64",
    "amd64": "x86_64",
    "x64": "x86_64",
}


def detect_target() -> str:
    system = platform.system().lower()  # darwin / linux / windows
    machine = platform.machine().lower()
    arch = _ARCH_ALIASES.get(machine, machine)
    return f"{system}-{arch}"


def _download(url: str) -> bytes:
    print(f"  downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "yt-downloader-build"})
    with urllib.request.urlopen(request) as response:  # noqa: S310 - trusted release hosts
        return response.read()


def _write_binary(path: str, data: bytes) -> None:
    with open(path, "wb") as out:
        out.write(data)
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  wrote {path} ({len(data) / 1024 / 1024:.1f} MB)")


def _extract_deno(zip_bytes: bytes, is_windows: bool) -> bytes:
    member = "deno.exe" if is_windows else "deno"
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = archive.namelist()
        match = next((name for name in names if name.endswith(member)), None)
        if match is None:
            raise RuntimeError(f"{member} not found in deno archive: {names}")
        return archive.read(match)


def fetch(target: str) -> None:
    if target not in _TARGETS:
        raise SystemExit(f"Unknown target {target!r}. Known: {', '.join(_TARGETS)}")
    is_windows = target.startswith("windows")
    ffmpeg_asset, deno_asset = _TARGETS[target]
    os.makedirs(DEST_DIR, exist_ok=True)

    print(f"Fetching binaries for {target} -> {DEST_DIR}")
    ffmpeg_name = "ffmpeg.exe" if is_windows else "ffmpeg"
    _write_binary(os.path.join(DEST_DIR, ffmpeg_name), _download(f"{_FFMPEG_BASE}/{ffmpeg_asset}"))

    deno_name = "deno.exe" if is_windows else "deno"
    deno_zip = _download(f"{_DENO_BASE}/{deno_asset}")
    _write_binary(os.path.join(DEST_DIR, deno_name), _extract_deno(deno_zip, is_windows))
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default=detect_target(),
        help=f"platform-arch to fetch (default: this host = {detect_target()}). "
        f"One of: {', '.join(_TARGETS)}",
    )
    args = parser.parse_args()
    fetch(args.target)


if __name__ == "__main__":
    sys.exit(main())
