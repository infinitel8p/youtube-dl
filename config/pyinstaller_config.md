# Building the executable

Run these from the repository root so the relative paths resolve. They assume the
project (and `pyinstaller`) is installed: `pip install -e ".[dev]"`.

The bundled data dirs (`themes/`, `ffmpeg-binaries/`, `config/`) are resolved at runtime
by `yt_downloader.resources.resource_path`, so they MUST be included via `--add-data`
with the same destination names. `--paths src` lets PyInstaller find the package.

## macOS / Linux

```bash
pyinstaller --onefile --noconfirm --windowed \
  --name "YouTube Downloader" \
  --paths src \
  --icon config/icon.ico \
  --add-data "themes:themes" \
  --add-data "ffmpeg-binaries/ffmpeg:ffmpeg-binaries" \
  --add-data "config/icon.ico:config" \
  --collect-data customtkinter \
  src/yt_downloader/__main__.py --clean
```

## Windows

```bat
pyinstaller --onefile --noconfirm --windowed ^
  --name "YouTube Downloader" ^
  --paths src ^
  --icon config\icon.ico ^
  --version-file config\version.rc ^
  --add-data "themes;themes" ^
  --add-data "ffmpeg-binaries\ffmpeg.exe;ffmpeg-binaries" ^
  --add-data "config\icon.ico;config" ^
  --collect-data customtkinter ^
  src\yt_downloader\__main__.py --clean
```

`--collect-data customtkinter` replaces the old hardcoded path to the site-packages
`customtkinter` directory, so the command no longer depends on the Python install
location.
