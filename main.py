from tkinter import filedialog
import customtkinter
import tempfile
import requests
import logging
import pytube
import io
import os
from PIL import Image

# Set up the logger
logger = logging.getLogger()
log_format = logging.Formatter('%(message)s\n')
logger.setLevel(logging.INFO)

# Create a handler to display log messages in the GUI


class TkinterHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.text_widget.configure(state='disabled')

    def emit(self, record):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(customtkinter.END, log_format.format(record))
        self.text_widget.see(customtkinter.END)
        self.text_widget.configure(state='disabled')


def progress_function(stream, chunk, file_handle, bytes_remaining):
    progress_bar["value"] = bytes_remaining


def download():
    global progress_bar
    progress_bar = customtkinter.CTkProgressBar(
        root, width=200, mode='determinate')
    progress_bar.pack()

    # Get the URL from the input widget
    url = url_input.get()
    logger.info(f'[ Downloading ] : {url}')

    # Create a YouTube object
    yt = pytube.YouTube(url, on_progress_callback=progress_function)

    r = requests.get(yt.thumbnail_url)
    if r.status_code == 200:
        thumbnail_image = Image.open(io.BytesIO(r.content))
        thumbnail = customtkinter.CTkImage(thumbnail_image, size=(150, 150))
        cover_label.configure(image=thumbnail)

    # Get the file name from the video title
    file_name = yt.title

    label.configure(text=f"Downloading: {yt.title}")

    # Add the .mp3 extension to the file name
    file_name = file_name + '.mp3'

    # Choose a file to save the audio
    file_path = filedialog.asksaveasfilename(
        title="Select audio file location", initialfile=file_name, filetypes=(("MP3 files", "*.mp3"),))
    file_path_parts = os.path.split(file_path)

    logger.info(f'[ Saving video to ] : {file_path_parts[0]}')

    # Download the audio to the selected file path
    video = yt.streams.filter(only_audio=True).first()

    video.download(file_path_parts[0], filename=file_path_parts[1])
    logger.info('[ Finished ] : Video downloaded')

    cover_label.configure(image=cover_tk)
    label.configure(text="Insert Video Link:")


# Create the GUI
root = customtkinter.CTk()
root.title('YouTube Downloader')
customtkinter.set_appearance_mode("dark")

# add thumbnail placeholder and iconbitmap
yt_icon = "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
r = requests.get(yt_icon)
if r.status_code == 200:
    cover_image = Image.open(io.BytesIO(r.content))
    cover_tk = customtkinter.CTkImage(cover_image, size=(150, 150))

with tempfile.NamedTemporaryFile(suffix='.ico', delete=False) as temp_file:
    cover_image.save(temp_file, format='ico')
root.iconbitmap(temp_file.name)

cover_label = customtkinter.CTkLabel(root, text="", image=cover_tk)
cover_label.pack(pady=(10, 0))

# add title label
label = customtkinter.CTkLabel(root, text="Insert Video Link:")
label.pack()

# add a frame for input and download button
grid = customtkinter.CTkFrame(root, fg_color="transparent")
grid.pack(padx=50, pady=(10, 10))

# Set up the URL input widget
url_input = customtkinter.CTkEntry(grid)
url_input.grid(row=0, column=0, padx=(0, 2.5))

# Set up the download button
download_button = customtkinter.CTkButton(
    grid, text='Download', command=download, width=50)
download_button.grid(row=0, column=1, padx=(2.5, 0))

# Set up the log output widget
log_output = customtkinter.CTkTextbox(root)
log_output.pack(side=customtkinter.BOTTOM,
                fill=customtkinter.BOTH, expand=True, padx=5, pady=5)

# Add the TkinterHandler to the logger
handler = TkinterHandler(log_output)
logger.addHandler(handler)


# Run the GUI
root.mainloop()

# https://www.youtube.com/watch?v=W5dHTc03oKs
