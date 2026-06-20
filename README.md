# youtube-dl
A simple desktop YouTube Downloader. The UI is a web frontend (Astro + Tailwind + Svelte) hosted in a native OS webview via pywebview; the backend relies on the yt-dlp library to download videos from YouTube and other sites.

A list of the theorethically supported sites can be found here: [List of supported Sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## Installation
### How to run on Windows
Download the `YouTube.Downloader.Windows.zip` and unzip it.
Now follow these steps:
1. Open the .exe
2. Click on More Informatiton in the Microsoft Defender SmartScreen Popup
3. Click on Run Anyway

### How to run on Mac
Download the `YouTube.Downloader.Darwin.zip` and unzip it.
Now follow these steps:
1. In the Finder on your Mac, locate the app you want to open.  
   Don’t use Launchpad to do this. Launchpad doesn’t allow you to access the shortcut menu.
2. Control-click the app icon.
3. Click Open in the shortcut menu .
   The app is saved as an exception to your security settings, and you can open it in the future by double-clicking it just as you can any registered app.

source: https://support.apple.com/de-de/guide/mac-help/mh40616/mac

## Run from source
Requires Python 3.10+ and Node 20+ with pnpm (the repo provisions both via [mise](https://mise.jdx.dev)).

```bash
pip install -e ".[dev]"            # or: pip install -r requirements.txt
pnpm --dir web install             # frontend deps
pnpm --dir web run build           # build the UI to web/dist (required before launching)
python scripts/fetch_binaries.py   # download ffmpeg + deno for your OS/arch into ffmpeg-binaries/
python -m yt_downloader
```

`scripts/fetch_binaries.py` fetches a static ffmpeg (for merging/remuxing) and deno (the
JavaScript runtime current YouTube extraction needs); these are not committed to git. The app
puts them on PATH at startup so downloads work without any system install.

To iterate on the UI in a plain browser (with a mock backend): `pnpm --dir web run dev`.

Run the tests with `pytest`. Build instructions for standalone executables are in [config/pyinstaller_config.md](config/pyinstaller_config.md).