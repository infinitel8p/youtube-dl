pyinstaller --onefile --noconfirm --windowed --icon "/Users/ludo/Documents/youtube-dl/config/icon.ico" --name "YouTube Downloader" --add-data "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/customtkinter:customtkinter/" --add-data "/Users/ludo/Documents/youtube-dl/ffmpeg-binaries:ffmpeg-binaries" --add-data "/Users/ludo/Documents/youtube-dl/modules:modules" --add-data "/Users/ludo/Documents/youtube-dl/themes:themes" main.pyw --clean