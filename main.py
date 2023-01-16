from pydub import AudioSegment
from tkinter import filedialog
import customtkinter
import subprocess
import platform
import tempfile
import requests
import logging
import pytube.request
import pytube
import io
import os
from PIL import Image


# Create a handler to display log messages in the GUI


class TkinterHandler(logging.Handler):
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

        # Set up the logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        # change chunk size to 25 kilobytes to have working progressbar even on small files
        pytube.request.default_range_size = 25600

        # Determine the operating system
        current_os = platform.system()

        if current_os == "Windows":
            self.ffmpeg_path = f"{os.path.dirname(os.path.abspath(__file__))}\\ffmpeg.exe"
        elif current_os == "Darwin":
            self.ffmpeg_path = f"{os.path.dirname(os.path.abspath(__file__))}\\ffmpeg"

        # Create the GUI
        self.title('YouTube Downloader')
        customtkinter.set_appearance_mode("dark")

        # add thumbnail placeholder and iconbitmap
        self.yt_icon = "https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
        self.r = requests.get(self.yt_icon)
        if self.r.status_code == 200:
            self.cover_image = Image.open(io.BytesIO(self.r.content))
            self.cover_tk = customtkinter.CTkImage(
                self.cover_image, size=(150, 150))

        with tempfile.NamedTemporaryFile(suffix='.ico', delete=False) as temp_file:
            self.cover_image.save(temp_file, format='ico')
        self.iconbitmap(temp_file.name)

        self.cover_label = customtkinter.CTkLabel(
            self, text="", image=self.cover_tk)
        self.cover_label.pack(pady=(10, 0))

        # add title label
        self.label = customtkinter.CTkLabel(self, text="Insert Video Link:")
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
        self.grid_2.pack(padx=50, pady=(10, 10), side=customtkinter.BOTTOM)

        self.playlist_slider = customtkinter.CTkSwitch(
            self.grid_2, text="Playlist")
        self.playlist_slider.grid(row=1, column=0)

        self.subtype_menu = customtkinter.CTkOptionMenu(self.grid_2, width=100, values=[
            "3gp", "aac", "flv", "m4a", "mp3", "mp4", "ogg", "wav", "webm"], command=self.set_subtype)
        self.subtype_menu.set("mp4")
        self.subtype_menu.grid(row=1, column=1)

        # add a frame for input and download button
        self.grid_1 = customtkinter.CTkFrame(self, fg_color="transparent")
        self.grid_1.pack(padx=50, pady=(10, 10), side=customtkinter.BOTTOM)

        # Set up the URL input widget
        self.url_input = customtkinter.CTkEntry(
            self.grid_1, width=250, font=("Arial", 10))
        self.url_input.grid(row=0, column=0, padx=(0, 2.5))

        # Set up the download button
        self.download_button = customtkinter.CTkButton(
            self.grid_1, text='Download', command=self.download, width=50)
        self.download_button.grid(row=0, column=1, padx=(2.5, 0))

    def set_subtype(self, event):
        self.subtype_menu.set(event)

    def download(self):
        self.downloaded = False

        if self.playlist_slider.get() == 0:
            try:
                # Get the URL from the input widget
                self.url = self.url_input.get()
                self.logger.info(f'[ Analyzing ] : {self.url}')

                # Create a YouTube object
                self.yt = pytube.YouTube(
                    self.url, on_progress_callback=self.progress_function, on_complete_callback=self.completed_function)

                # set cover_label to video thumbnail
                self.r = requests.get(self.yt.thumbnail_url)
                if self.r.status_code == 200:
                    self.thumbnail_image = Image.open(
                        io.BytesIO(self.r.content))
                    self.thumbnail = customtkinter.CTkImage(
                        self.thumbnail_image, size=(150, 150))
                    self.cover_label.configure(image=self.thumbnail)

                # Get the file name from the video title
                self.file_name = self.yt.title
                self.label.configure(text=f"Downloading: {self.file_name}")

                # create a progressbar
                self.progress_bar = customtkinter.CTkProgressBar(
                    self, width=325, mode='determinate')
                self.progress_bar.pack()
                self.progress_bar.set(0)

                # Find audio and select file path
                self.video = self.yt.streams.filter(
                    only_audio=True, subtype=self.subtype_menu.get()).order_by('abr').desc().first()
                if self.video is None:
                    self.logger.info(
                        f"[ Error ] : {self.subtype_menu.get()} subtype not available for this video. Video will be downloaded in mp4 and converted to {self.subtype_menu.get()}")

                    self.video = self.yt.streams.filter(
                        only_audio=True, subtype="mp4").order_by('abr').desc().first()

                    # Add the .mp4 extension to the file name
                    self.file_name = f"{self.file_name}.mp4"

                    # Choose a file to save the audio
                    self.file_path = filedialog.asksaveasfilename(
                        title="Select audio file location", initialfile=self.file_name, filetypes=(("Audio files", f"*mp4"),))
                    self.file_path_parts = os.path.split(self.file_path)

                    self.logger.info(
                        f'[ Saving video to ] : {self.file_path_parts[0]}')
                    self.logger.info(
                        f'[ Downloading ] : {self.file_path_parts[1]}')

                    # download
                    self.video.download(
                        self.file_path_parts[0], filename=self.file_path_parts[1])

                    # Open the MP4 file and convert it to selected format
                    while not self.downloaded:
                        pass

                    self.logger.info(
                        f'[ Converting ] : {self.file_path_parts[1]} to .{self.subtype_menu.get()} format')
                    self.new_file = self.file_path.replace(
                        "mp4", self.subtype_menu.get())

                    # convert the file using ffmpeg and delete initial .mp4
                    with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
                        self.thumbnail_image.save(temp_file, format='jpeg')

                    subprocess.run(
                        f'ffmpeg -i "{self.file_path}" "{os.path.join(self.file_path_parts[0], f"temp_convert.{self.subtype_menu.get()}")}"', shell=True, check=True)
                    self.conversion = subprocess.run(
                        f'ffmpeg -i "{os.path.join(self.file_path_parts[0], f"temp_convert.{self.subtype_menu.get()}")}" -i {temp_file.name} -map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover(Front)" "{self.new_file}"')

                    if self.conversion.returncode == 0:
                        os.remove(self.file_path)
                        os.remove(
                            os.path.join(self.file_path_parts[0], f"temp_convert.{self.subtype_menu.get()}"))

                    self.logger.info('[ Finished ] : Video downloaded')

                else:
                    # Add the extension to the file name
                    self.file_name = f"{self.file_name}.{self.subtype_menu.get()}"

                    # Choose a file to save the audio
                    self.file_path = filedialog.asksaveasfilename(
                        title="Select audio file location", initialfile=self.file_name, filetypes=(("Audio files", f"*{self.subtype_menu.get()}"),))
                    self.file_path_parts = os.path.split(self.file_path)

                    self.logger.info(
                        f'[ Saving video to ] : {self.file_path_parts[0]}')

                    self.temp_audio = self.file_path_parts[1].replace(
                        ".mp4", "_temp.mp4")

                    # download
                    self.video.download(
                        self.file_path_parts[0], filename=self.temp_audio)

                    # Open the MP4 file and convert it to selected format
                    while not self.downloaded:
                        pass

                    # convert the file using ffmpeg and delete initial .mp4
                    with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
                        self.thumbnail_image.save(temp_file, format='jpeg')

                    self.conversion = subprocess.run(
                        f'ffmpeg -i "{os.path.join(self.file_path_parts[0], self.temp_audio)}" -i "{temp_file.name}" -map 1 -map 0 -c copy -disposition:0 attached_pic "{self.file_path}"')

                    if self.conversion.returncode == 0:
                        os.remove(os.path.join(
                            self.file_path_parts[0], self.temp_audio))

                    self.logger.info('[ Finished ] : Video downloaded')

                # set cover and label to inital values
                self.cover_label.configure(image=self.cover_tk)
                self.label.configure(text="Insert Video Link:")
                self.progress_bar.destroy()

            except pytube.exceptions.RegexMatchError:
                self.logger.info("[ Error ] : Could not find link")

    def progress_function(self, stream, chunk, bytes_remaining):
        self.percentage_completed = (
            stream.filesize - bytes_remaining) / stream.filesize
        self.progress_bar.set(self.percentage_completed)
        self.progress_bar.update()

    def completed_function(self, stream, file_path):
        self.downloaded = True
        print(stream)


if __name__ == "__main__":
    # Run the GUI
    app = Root()
    app.mainloop()

# https://www.youtube.com/watch?v=W5dHTc03oKs
