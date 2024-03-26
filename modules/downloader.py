import ffmpeg
import logging
import platform
import threading
import customtkinter
from yt_dlp import YoutubeDL

logger = logging.getLogger("yt-dlp_app_logger")


class YTDLLogger(object):
    def info(self, msg):
        logger.info(msg)

    def debug(self, msg):
        if "[download]" not in msg:
            logger.debug(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)


def download(root_application, url, format):
    """Download a video from a given URL and convert it to the specified format.

    Args:
        root_application (customtkinter.CTk): The root customtkinter application
        url (str): The URL of the video to download
        format (str): One of the following formats: mp3, mp4, aac, ogg, flv, 3gp, m4a, webm, wav
    """
    logger.info("Download complete.")

    # binary path
    current_os = platform.system()
    ffmpeg_path = root_application.resource_path("ffmpeg-binaries/ffmpeg")

    if current_os == "Windows":
        ffmpeg_path = ffmpeg_path + ".exe"

    def progress_hook(d):
        """A closure that can access root_application's progress_bar."""
        if d['status'] == 'downloading':
            if d['total_bytes']:
                progress = d['downloaded_bytes'] / d['total_bytes']
                root_application.after(
                    0, lambda: root_application.progress_bar.set(progress))
        elif d['status'] == 'finished':
            root_application.after(
                0, lambda: root_application.progress_bar.set(1))

    def postprocessor_hooks(d):
        if d['status'] == 'started':
            # logger.info("Postprocessing started.")
            pass
        elif d['status'] == 'finished':
            logger.info("Postprocessing finished.")
        else:
            logger.info(f"Unknown status: {d['status']}")

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
        }

        with YoutubeDL(options) as ydl:
            ydl.download(["https://www.youtube.com/watch?v=FAyKDaXEAgc"])

        logger.info("Download complete.")

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
