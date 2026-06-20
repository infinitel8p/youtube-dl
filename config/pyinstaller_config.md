# Building the executable

Run these from the repository root so the relative paths resolve. They assume the
project (and `pyinstaller`) is installed: `pip install -e ".[dev]"`.

**Build the frontend and fetch the runtime binaries first.** The UI is an Astro/Svelte app
under `web/` (PyInstaller bundles the compiled output), and `ffmpeg-binaries/` must hold the
ffmpeg + deno binaries for the target platform (not committed to git):

```bash
npm --prefix web ci
npm --prefix web run build                 # produces web/dist/
python scripts/fetch_binaries.py           # fills ffmpeg-binaries/ for THIS os/arch
# cross-building? pass e.g. --target windows-x86_64
```

`web/dist/`, `ffmpeg-binaries/`, and `config/icon.ico` are resolved at runtime by
`yt_downloader.resources.resource_path`, so they MUST be included via `--add-data` with the
same destination names. The whole `ffmpeg-binaries/` directory is bundled so ffmpeg, ffprobe
(if present), and deno all ship; at startup the app prepends it to PATH so yt-dlp finds them. `--paths src` lets PyInstaller find the package, and
`--collect-all webview` pulls in pywebview's platform backend (WKWebView/macOS,
EdgeChromium/Windows) plus its data files.

## macOS / Linux

```bash
pyinstaller --onefile --noconfirm --windowed \
  --name "YouTube Downloader" \
  --paths src \
  --icon config/icon.ico \
  --add-data "web/dist:web/dist" \
  --add-data "ffmpeg-binaries:ffmpeg-binaries" \
  --add-data "config/icon.ico:config" \
  --collect-all webview \
  src/yt_downloader/__main__.py --clean
```

## Windows

```bat
pyinstaller --onefile --noconfirm --windowed ^
  --name "YouTube Downloader" ^
  --paths src ^
  --icon config\icon.ico ^
  --version-file config\version.rc ^
  --add-data "web\dist;web\dist" ^
  --add-data "ffmpeg-binaries;ffmpeg-binaries" ^
  --add-data "config\icon.ico;config" ^
  --collect-all webview ^
  src\yt_downloader\__main__.py --clean
```

Notes:
- **Windows needs the WebView2 runtime.** It is evergreen and present on essentially all
  Win10/11 machines; for older targets bundle the Evergreen Bootstrapper alongside the exe.
- `--collect-all webview` replaces the old `--collect-data customtkinter`. If the frozen app
  starts with a blank window, double-check that `web/dist/index.html` landed in the bundle and
  that the webview backend was collected.
- The frontend uses absolute asset URLs (`/_astro/...`); pywebview serves `web/dist` over its
  bundled http server (`webview.start(http_server=True)`), so those paths resolve in the bundle.
