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

    def info(self, msg):
        logger.info(msg)

    def debug(self, msg):
        if "[download]" not in msg:
            logger.debug(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)


def download(root_application, url, format, download_dir, filename=None):
    """Download a video from a given URL and convert it to the specified format, then save it to the chosen location with the specified filename.

    Args:
        root_application (customtkinter.CTk): The root customtkinter application.
        url (str): The URL of the video to download.
        format (str): The desired output format (e.g., 'mp3', 'mp4').
        download_dir (str): The path to save the downloaded video to.
        filename (str, optional): The name of the file to save the video as. Defaults to None.
    """
    logger.info("[Info] Download initiated.")

    # binary path
    current_os = platform.system()
    ffmpeg_path = root_application.resource_path("ffmpeg-binaries/ffmpeg")

    if current_os == "Windows":
        ffmpeg_path = ffmpeg_path + ".exe"

    def progress_hook(d):
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

    def postprocessor_hooks(d):
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
        # Set common options
        options = {
            'ffmpeg_location': ffmpeg_path,
            'format': 'bestvideo+bestaudio',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': format,
            }],
            'logger': YTDLLogger(),
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hooks],
            'ignoreerrors': True,
        }

        # If download of playlist disabled, download only the first video
        if filename:
            options['playlist_items'] = '1'
            options['outtmpl'] = f"{download_dir}/{filename}.%(ext)s"
        else:
            options['outtmpl'] = f"{download_dir}/%(title)s.%(ext)s"
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info and not filename:  # It's a playlist and no specific filename is given
                    first_video_url = info['entries'][0]['webpage_url']
                    ydl.download([first_video_url])
                else:
                    ydl.download([url])
        except DownloadError as e:
            logger.error(f"[Error] {e}")
            return
        logger.info("[Info] Download complete.")

        # Use after method to safely interact with the UI from the other thread
        root_application.after(0, root_application.progress_bar.destroy)
        root_application.label = customtkinter.CTkLabel(
            root_application.top_grid, text="Insert Video Link:")
        root_application.label.pack()
        root_application.after(0, root_application.download_button.configure(
            state=customtkinter.NORMAL))

    # Create and start the download thread
    thread = threading.Thread(target=download_thread)
    thread.start()
