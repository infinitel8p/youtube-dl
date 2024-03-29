import ffmpeg
import logging
import platform
import threading
import customtkinter
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

logger = logging.getLogger("yt-dlp_app_logger")


class YTDLLogger(object):
    """
    A custom logger for the YouTube downloader.

    Args:
        object (object): The base object class. Does not need to be explicitly passed.
    """

    def __init__(self, root_application=None):
        self.root_application = root_application

    def info(self, msg):
        logger.info(msg)

    def debug(self, msg):
        if "[download]" not in msg:
            logger.debug(msg)
        if any(keyword in msg for keyword in ["[Merger]", "[VideoConvertor]"]):
            logger.debug("This could take a while...")
        custom_messages = {
            "[youtube:tab] Extracting URL": "Analyzing...",
            "format(s)": "Downloading...",
            "[Merger]": "Merging...",
            "[VideoConvertor]": "Converting...",
            "[EmbedSubtitle]": "Embedding subtitles..."
        }
        for keyword, custom_message in custom_messages.items():
            if keyword in msg and self.root_application:
                self.root_application.label.configure(
                    text=custom_message)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)


def download(root_application: customtkinter.CTk, url: str, file_format: str, try_subtitles: int, download_dir: str, filename: str = None):
    """Download a video from a given URL and convert it to the specified format, then save it to the chosen location with the specified filename.

    Args:
        root_application (customtkinter.CTk): The root customtkinter application.
        url (str): The URL of the video to download.
        file_format (str): The desired output format (e.g., 'mp3', 'mp4').
        try_subtitles (int): Whether to download subtitles or not. 1 for yes, 0 for no.
        download_dir (str): The path to save the downloaded video to.
        filename (str, optional): The name of the file to save the video as. Defaults to None.
    """
    logger.info("[Info] Download initiated.")

    # binary path
    current_os = platform.system()
    ffmpeg_path = root_application.resource_path("ffmpeg-binaries/ffmpeg")

    if current_os == "Windows":
        ffmpeg_path = ffmpeg_path + ".exe"

    def progress_hook(d: dict):
        """
        A closure that can access root_application's progress_bar.

        Args:
            d (dict): A dictionary containing the download status and progress.
        """

        if d['status'] == 'downloading':
            try:
                if d['total_bytes']:
                    progress = d['downloaded_bytes'] / d['total_bytes']
                    root_application.after(
                        0, lambda: root_application.progress_bar.set(progress))
            except KeyError:
                root_application.after(
                    0, lambda: root_application.progress_bar.set(0))
        elif d['status'] == 'finished':
            root_application.after(
                0, lambda: root_application.progress_bar.set(1))

    def postprocessor_hooks(d: dict):
        """
        A closure for postprocessing hooks.

        Args:
            d (dict): A dictionary containing the download status and progress.
        """

        if d['status'] == 'started':
            logger.info(
                f"[Status] Postprocessing started: {d['postprocessor']}")
        elif d['status'] == 'finished':
            logger.info(
                f"[Status] Postprocessing finished: {d['postprocessor']}")
        else:
            logger.info(f"[Status] Unknown status: {d['status']}")

    def download_thread():
        """
        A thread to download the video.
        """

        # Set common options
        options = {
            'ffmpeg_location': ffmpeg_path,
            'logger': YTDLLogger(root_application),
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hooks],
            'ignoreerrors': True,
        }
        postprocessors = []

        # Set output format
        if file_format in ['mp3', 'aac', 'ogg', 'm4a', 'wav']:
            options['format'] = 'bestaudio'
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': file_format,
            })
        elif file_format in ['mp4', 'flv', '3gp', 'webm', 'mkv']:
            options['format'] = 'bestvideo+bestaudio'
            postprocessors.append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': file_format,
            })

        options['postprocessors'] = postprocessors

        # If download of playlist disabled, download only the first video
        if filename:
            options['playlist_items'] = '1'
            options['outtmpl'] = f"{download_dir}/{filename}.%(ext)s"
        else:
            options['outtmpl'] = f"{download_dir}/%(title)s.%(ext)s"

        # If subtitles are requested, download them
        if try_subtitles == 1:
            options['writesubtitles'] = True
            options['allsubtitles'] = True
            postprocessors.append({'already_have_subtitle': False,
                                   'key': 'FFmpegEmbedSubtitle'},)

        try:
            with YoutubeDL(options) as ydl:
                ydl.download([url])
        except DownloadError as e:
            logger.error(f"[Error] {e}")
            return
        logger.info("[Info] Download complete.")

        # Use after method to safely interact with the UI from the other thread
        root_application.after(0, root_application.progress_bar.destroy)
        root_application.title_label = customtkinter.CTkLabel(
            root_application.progress_bar_grid, text=f"YouTube Downloader v{root_application.version}", font=("Arial", 20))
        root_application.title_label.pack()
        root_application.label.configure(text="Insert Video Link:")
        root_application.after(0, root_application.download_button.configure(
            state=customtkinter.NORMAL))

    # Create and start the download thread
    thread = threading.Thread(target=download_thread)
    thread.start()
