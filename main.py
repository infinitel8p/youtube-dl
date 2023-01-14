from tkinter import filedialog
import customtkinter
import tempfile
import requests
import logging
import pytube
import pytube.request
import io
import os
from PIL import Image

# Set up the logger
logger = logging.getLogger()
log_format = logging.Formatter('%(message)s\n')
logger.setLevel(logging.INFO)

# change chunk size to 25 kilobytes to have working progressbar even on small files
pytube.request.default_range_size = 25600

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
        self.text_widget.update()  # Refresh the widget


def progress_function(stream, chunk, bytes_remaining):
    percentage_completed = (
        stream.filesize - bytes_remaining) / stream.filesize
    progress_bar.set(percentage_completed)
    progress_bar.update()


def completed_function(stream, file_path):
    logger.info('[ Finished ] : Video downloaded')


def download():
    try:
        # Get the URL from the input widget
        url = url_input.get()
        logger.info(f'[ Downloading ] : {url}')

        # Create a YouTube object
        yt = pytube.YouTube(url, on_progress_callback=progress_function,
                            on_complete_callback=completed_function)

        # set cover_label to video thumbnail
        r = requests.get(yt.thumbnail_url)
        if r.status_code == 200:
            thumbnail_image = Image.open(io.BytesIO(r.content))
            thumbnail = customtkinter.CTkImage(
                thumbnail_image, size=(150, 150))
            cover_label.configure(image=thumbnail)

        # Get the file name from the video title
        file_name = yt.title
        label.configure(text=f"Downloading: {file_name}")

        # create a progressbar
        global progress_bar
        progress_bar = customtkinter.CTkProgressBar(
            root, width=325, mode='determinate')
        progress_bar.pack()
        progress_bar.set(0)

        # Add the .mp3 extension to the file name
        file_name = file_name + f".{subtype_menu.get()}"

        # Choose a file to save the audio
        file_path = filedialog.asksaveasfilename(
            title="Select audio file location", initialfile=file_name, filetypes=(("Audio files", f"*{subtype_menu.get()}"),))
        file_path_parts = os.path.split(file_path)

        logger.info(f'[ Saving video to ] : {file_path_parts[0]}')

        # Download the audio to the selected file path
        try:
            video = yt.streams.filter(
                only_audio=True, subtype=subtype_menu.get()).order_by('abr').desc().first()
            if video is None:
                raise ValueError(
                    f"[ Error ] : {subtype_menu.get()} subtype not available for this video.")
            else:
                video.download(file_path_parts[0], filename=file_path_parts[1])
        except ValueError as e:
            logger.info(e)

        # set cover and label to inital values
        cover_label.configure(image=cover_tk)
        label.configure(text="Insert Video Link:")
        progress_bar.destroy()

    except pytube.exceptions.RegexMatchError:
        logger.info("[ Error ] : Could not find link")


def set_subtype(event):
    subtype_menu.set(event)


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

# Set up the log output widget
log_output = customtkinter.CTkTextbox(root)
log_output.pack(side=customtkinter.BOTTOM,
                fill=customtkinter.BOTH, expand=True, padx=5, pady=5)

# Add the TkinterHandler to the logger
handler = TkinterHandler(log_output)
logger.addHandler(handler)

# add a frame for input and download button
grid_1 = customtkinter.CTkFrame(root, fg_color="transparent")
grid_1.pack(padx=50, pady=(10, 10), side=customtkinter.BOTTOM)

# Set up the URL input widget
url_input = customtkinter.CTkEntry(grid_1, width=250, font=("Arial", 10))
url_input.grid(row=0, column=0, padx=(0, 2.5), pady=(0, 5))

# Set up the download button
download_button = customtkinter.CTkButton(
    grid_1, text='Download', command=download, width=50)
download_button.grid(row=0, column=1, padx=(2.5, 0), pady=(0, 5))

playlist_slider = customtkinter.CTkSwitch(grid_1, text="Playlist")
playlist_slider.grid(row=1, column=0, pady=(5, 0))

subtype_menu = customtkinter.CTkOptionMenu(grid_1, values=[
    "3gp", "aac", "flv", "m4a", "mp3", "mp4", "ogg", "wav", "webm"], command=set_subtype)
subtype_menu.set("mp4")
subtype_menu.grid(row=1, column=1, pady=(5, 0))

# Run the GUI
root.mainloop()

# https://www.youtube.com/watch?v=W5dHTc03oKs
