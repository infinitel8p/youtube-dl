import io
import os
import sys
import logging
import platform
import requests
import tempfile
import customtkinter
import modules.downloader as dl
from PIL import Image
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from tkinter import filedialog

version = "1.3"


class TkinterHandler(logging.Handler):
    """
    A custom logging handler that displays log messages in a Tkinter Text widget.

    Args:
        text_widget (customtkinter.CTkTextbox): The Text widget to display the log messages in.
    """

    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.text_widget.configure(state='disabled')
        self.log_format = logging.Formatter('%(message)s\n')

    def emit(self, record):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(
            customtkinter.END, self.log_format.format(record))
        self.text_widget.see(customtkinter.END)
        self.text_widget.configure(state='disabled')
        self.text_widget.update()  # Refresh the widget


class Root(customtkinter.CTk):

    def __init__(self):
        super().__init__()
        self.version = version

        # Set up the main application logger
        self.logger = logging.getLogger("yt-dlp_app_logger")
        self.logger.setLevel(logging.DEBUG)  # Capture all log messages

        # Create the GUI
        self.title('YouTube Downloader')
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme(
            self.resource_path(os.path.join("themes", "red.json")))
        self.resizable(False, False)
        self.geometry("550x550")

        # add thumbnail placeholder and iconbitmap
        self.yt_icon = "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
        self.r = requests.get(self.yt_icon)
        if self.r.status_code == 200:
            self.cover_image = Image.open(io.BytesIO(self.r.content))
            self.cover_tk = customtkinter.CTkImage(
                self.cover_image, size=(150, 150))

        with tempfile.NamedTemporaryFile(suffix='.ico', delete=False) as temp_file:
            self.cover_image.save(temp_file, format='ico')
        if platform.system() == "Windows":
            self.iconbitmap(temp_file.name)

        self.cover_label = customtkinter.CTkLabel(
            self, text="", image=self.cover_tk)
        self.cover_label.pack()

        # add frame for progress bar
        self.progress_bar_grid = customtkinter.CTkFrame(
            self, fg_color="transparent")
        self.progress_bar_grid.pack()

        self.title = customtkinter.CTkLabel(
            self.progress_bar_grid, text=f"YouTube Downloader v{version}", font=("Arial", 20))
        self.title.pack()

        # add frame for title label
        self.top_grid = customtkinter.CTkFrame(self, fg_color="transparent")
        self.top_grid.pack()

        # add title label
        self.label = customtkinter.CTkLabel(
            self.top_grid, text="Insert Video Link:")
        self.label.pack()

        # Set up the log output widget
        self.log_output = customtkinter.CTkTextbox(self)
        self.log_output.pack(side=customtkinter.BOTTOM,
                             fill=customtkinter.BOTH, expand=True, padx=5, pady=5)

        # Add the TkinterHandler to the logger
        self.handler = TkinterHandler(self.log_output)
        self.logger.addHandler(self.handler)

        # add a frame for download options
        self.grid_2 = customtkinter.CTkFrame(self, fg_color="transparent")
        self.grid_2.pack(padx=50, pady=(10, 10),
                         side=customtkinter.BOTTOM)

        self.playlist_slider = customtkinter.CTkSwitch(
            self.grid_2, text="Playlist")
        self.playlist_slider.grid(row=1, column=0)

        self.subtype_menu = customtkinter.CTkOptionMenu(self.grid_2, width=100, values=[
            # flac missing, maybe use ffmpeg to convert
            "mp3", "mp4", "aac", "ogg", "flv", "3gp", "m4a", "webm", "wav", "mkv"], command=self.set_subtype)
        self.subtype_menu.set("mp4")
        self.subtype_menu.grid(row=1, column=1)

        # add a frame for input and download button
        self.grid_1 = customtkinter.CTkFrame(self, fg_color="transparent")
        self.grid_1.pack(padx=50, pady=(10, 10),
                         side=customtkinter.BOTTOM)

        # Set up the URL input widget
        self.url_input = customtkinter.CTkEntry(
            self.grid_1, width=350, font=("Arial", 10))
        self.url_input.grid(row=0, column=0, padx=(0, 2.5))

        # Set up the download button
        self.download_button = customtkinter.CTkButton(
            self.grid_1, text='Download', command=self.start_download, width=50)
        self.download_button.grid(row=0, column=1, padx=(2.5, 0))

        self.logger.info(f"[Info] YouTube Downloader GUI v{version} started.")

    def resource_path(self, relative_path: str):
        """
        Get absolute path to resource, works for dev and for PyInstaller

        Args:
            relative_path (str): The relative path to the resource.
        Returns:
            str: The absolute path to the resource.
        """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    def set_subtype(self, event: str):
        """Set the subtype of the video to download

        Args:
            event (str): The subtype of the video to download.
        """
        self.subtype_menu.set(event)

    def start_download(self):
        """
        Start the download process

        This method is called when the user clicks the download button.
        """

        def fetch_video_title(url: str):
            """
            Fetch the title of the video to be downloaded

            Args:
                url (str): The URL of the video to download.

            Returns:
                str: The title of the video.
            """
            self.logger.info(
                f'[Analyzing] Fetching video title: {url}\nThis could take a few seconds!')

            options = {
                'playlist_items': '1',
            }
            try:
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=False)

                    if 'entries' in info:
                        # if playlist, get the first video title
                        first_video_info = info['entries'][0] if info['entries'] else {
                        }
                        return first_video_info.get('title', 'Download')
                    else:
                        return info.get('title', 'Download')
            except DownloadError as e:
                self.logger.error(
                    f"[Error] Could not fetch video title: {e}")
                return "Download"

        # check if is playlist, if not the ask for filename
        if self.playlist_slider.get() == 1:
            self.logger.info("[Info] Downloading playlist.")
            self.download_dir = filedialog.askdirectory()
            self.filename = None

            if not self.download_dir:
                self.logger.warning("[Warning] Download cancelled.")
                return
        else:
            self.logger.info("[Info] Downloading single video.")
            # Setting up the save dialog with prefill filename
            filetypes = [(f"{self.subtype_menu.get().upper()} files",
                          # ("All files", "*.*")
                          f"*.{self.subtype_menu.get()}"), ]
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{self.subtype_menu.get()}", filetypes=filetypes, initialfile=fetch_video_title(self.url_input.get()))

            if not file_path:
                self.logger.warning("[Warning] Download cancelled.")
                return

            self.download_dir, self.filename_with_extension = os.path.split(
                file_path)
            self.filename, self.extension = os.path.splitext(
                self.filename_with_extension)

        self.title.destroy()
        self.progress_bar = customtkinter.CTkProgressBar(
            self.progress_bar_grid, mode='determinate', width=250)
        self.progress_bar.pack(pady=(10, 10))
        self.progress_bar.set(0)
        self.download_button.configure(state=customtkinter.DISABLED)

        dl.download(self, self.url_input.get(),
                    self.subtype_menu.get(), self.download_dir, self.filename)


if __name__ == "__main__":
    # Run the GUI
    app = Root()
    app.mainloop()
    # testurl = https://www.youtube.com/watch?v=FAyKDaXEAgc
