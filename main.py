import os
import pytube
from tkinter import filedialog
import logging

import customtkinter

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_format = logging.Formatter('%(message)s\n')

# Create a handler to display log messages in the GUI


class TkinterHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        self.text_widget.insert(customtkinter.END, log_format.format(record))
        self.text_widget.see(customtkinter.END)


# Create the GUI
root = customtkinter.CTk()
root.title('YouTube Downloader')

# Set up the log output widget
log_output = customtkinter.CTkTextbox(root)
log_output.pack(side=customtkinter.BOTTOM,
                fill=customtkinter.BOTH, expand=True)

# Add the TkinterHandler to the logger
handler = TkinterHandler(log_output)
logger.addHandler(handler)

# Set up the URL input widget
url_input = customtkinter.CTkEntry(root)
url_input.pack(side=customtkinter.LEFT)

# Set up the download button


def download():
    # Get the URL from the input widget
    url = url_input.get()
    logger.info(f'Downloading video from {url}')

    # Create a YouTube object
    yt = pytube.YouTube(url)

    # Get the audio streams
    audio_streams = yt.streams.filter(only_audio=True)

    # Choose the first audio stream
    audio = audio_streams.first()

    # Get the file name from the video title
    file_name = yt.title

    # Remove any invalid characters from the file name
    #file_name = ''.join(c for c in file_name if c.isalnum() or c in (' ', '.'))

    # Add the .mp3 extension to the file name
    file_name = file_name + '.mp3'

    # Choose a file to save the audio
    file_path = filedialog.asksaveasfilename(
        title="Select audio file location", initialfile=file_name, filetypes=(("MP3 files", "*.mp3"),))
    logger.info(f'Saving video to {file_path}')

    # Download the audio to the selected file path
    audio.download(filename=file_path)
    logger.info('Video downloaded')


download_button = customtkinter.CTkButton(
    root, text='Download', command=download)
download_button.pack(side=customtkinter.LEFT)

# Run the GUI
root.mainloop()
