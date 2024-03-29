import customtkinter
import subprocess
import tempfile
import requests
import platform
import json
import time
import sys
import os


class UpdateUi(customtkinter.CTkToplevel):
    """This class is used to create a pop-up window to inform the user that a new version of the application is available and ask if they want to update.
    Attributes:
        updating (bool): A flag to indicate whether the update process is currently in progress
        parent (customtkinter.CTkToplevel): The parent window of this class
        background (CTkFrame): The background frame of the window
        label1 (CTkLabel): Label that displays the current and latest version of the application
        label2 (CTkLabel): Label that asks the user if they want to update
        button_grid (CTkFrame): Frame that contains the "Yes" and "No" buttons
        button1 (CTkButton): "No" button
        button2 (CTkButton): "Yes" button
    Methods:
        __init__(self, parent): Initializes the class by creating the window, setting its properties, creating the UI elements and adding the
        "Yes" and "No" buttons.
        add_output(self, text): Add text to the output textbox
        update(self, event=None): The function that downloads and installs the update. Defaults to `None`.
    """

    def __init__(self, parent: customtkinter.CTkToplevel):
        """Initializes the class by creating the window, setting its properties, creating the UI elements and adding the "Yes" and "No" buttons.
        Args:
            parent (customtkinter.CTkToplevel): The parent window of this class.
        """

        # Main Frame
        super().__init__(parent)
        self.wm_title("Update Required")
        self.attributes("-topmost", True)
        self.parent = parent
        self.updating = False

        self.url = "https://api.github.com/repos/infinitel8p/youtube-dl/releases"
        # TODO executable is expected to be named self.name or the code will fail, maybe recheck logic in future
        self.name = "YouTube Downloader"

        if platform.system() == "Windows":
            self.attributes("-toolwindow", 1)
            # self.name, _ = os.path.splitext(os.path.basename(sys.executable))
        elif platform.system() == "Darwin":
            # self.name, _ = os.path.splitext(os.path.basename(os.path.dirname(os.path.dirname(sys.executable))))
            pass

        self.background = customtkinter.CTkFrame(
            self, bg_color=['gray92', 'gray14'], corner_radius=6)
        self.background.pack(padx=10, pady=10)

        # Set the label font and text size
        self.label1 = customtkinter.CTkLabel(
            self.background,
            text=f"A new version of the application is available.\nCurrent version: {self.parent.version} | Latest release: {self.parent.latest_version}",
            font=("Arial", 14, "bold"))
        self.label1.pack(padx=10, pady=5)

        self.label2 = customtkinter.CTkLabel(
            self.background, text="Would you like to update?")
        self.label2.pack(pady=5)

        self.button_grid = customtkinter.CTkFrame(
            self, fg_color="transparent")
        self.button_grid.pack(pady=(10, 15), side=customtkinter.BOTTOM)

        self.button1 = customtkinter.CTkButton(
            self.button_grid, text="No", command=self.destroy, width=90)
        self.button1.grid(row=0, column=0, padx=(0, 5))

        self.button2 = customtkinter.CTkButton(
            self.button_grid, text="Yes", command=self.update, width=90)
        self.button2.grid(row=0, column=1, padx=(5, 0))

    def add_output(self, text: str):
        """
        Add text to the output textbox
        Parameters:
            text (str): The text to be added to the output textbox
        """

        self.output.configure(state='normal')
        self.output.insert(
            customtkinter.END, text)
        self.output.see(customtkinter.END)
        self.output.configure(state='disabled')
        self.background.update()

    def format_speed(self, bytes, seconds):
        """Calculate and format speed without padding spaces."""
        if seconds > 0:
            speed = bytes / seconds
            if speed < 1024:
                unit = "B/s"
            elif speed < 1024**2:
                speed /= 1024
                unit = "KB/s"
            else:
                speed /= 1024**2
                unit = "MB/s"
            return f"{speed:.2f} {unit}".rstrip()
        else:
            return "Calculating..."

    def format_file_size(self, bytes):
        """Format file size without padding spaces."""
        if bytes < 1024:
            size = bytes
            unit = "B"
        elif bytes < 1024**2:
            size = bytes / 1024
            unit = "KB"
        elif bytes < 1024**3:
            size = bytes / 1024**2
            unit = "MB"
        else:
            size = bytes / 1024**3
            unit = "GB"
        return f"{size:.2f} {unit}".rstrip()

    def update(self, event=None):
        """
        The function that downloads and installs the update

        Parameters:
            event (_type_): The event that triggered the function call. This is usually an event such as a button press
            and is automatically passed by the function call. Defaults to `None`.
        """

        self.updating = True
        self.button1.destroy()
        self.button2.destroy()
        self.button_grid.destroy()
        self.label2.destroy()

        self.output = customtkinter.CTkTextbox(self.background)
        self.output.pack(padx=5, pady=5, fill=customtkinter.BOTH, expand=True)
        self.output.configure(state='disabled')

        self.add_output("Prepairing update...\n\n")
        time.sleep(0.5)

        # Detect OS (supports Windows and macOS)
        os_name = platform.system()
        if os_name == "Windows":
            self.add_output("Detected Windows OS.\n\n")
        elif os_name == "Darwin":
            self.add_output("Detected macOS OS.\n\n")
        else:
            self.add_output(
                f"Unsupported OS detected ({os_name}). Please update manually.\n\nClosing setup in 5 sec...")
            time.sleep(5)
            self.destroy()

        # Prepare download directory
        temp_dir = tempfile.gettempdir()
        download_path = os.path.join(os.path.join(os.path.join(
            os.path.dirname(temp_dir), self.name), "Updates"), f"Update {self.parent.latest_version}")
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        self.add_output(f"Download directory created at:\n{download_path}\n\n")

        try:
            # Fetch release information
            releases_response = requests.get(self.url)
            releases_data = json.loads(releases_response.text)
            assets_response = requests.get((releases_data[0]["assets_url"]))
            assets_data = json.loads(assets_response.text)
            # find asst with os_name in the name
            for asset in assets_data:
                if os_name in asset["name"]:
                    download_url = asset["browser_download_url"]
                    break
            else:
                self.add_output(
                    f"Could not find a suitable download for {os_name}.\n\nClosing setup in 5 sec...")
                time.sleep(5)
                self.destroy()

            # Prepare for downloading
            response = requests.get(download_url, stream=True)
            total_length = response.headers.get('content-length')

            if total_length is None:  # No content length header
                self.add_output(
                    "Cannot determine file size for progress tracking.\n\n")
                open(os.path.join(download_path, f"{self.name}.zip"),
                     'wb').write(response.content)
            else:
                # Create and display the progress bar
                total_length = int(total_length)
                downloaded = 0

                self.progress_bar = customtkinter.CTkProgressBar(
                    self.background)
                self.progress_bar.pack(padx=5, pady=(
                    0, 5), fill=customtkinter.X, expand=True)
                self.download_status_label = customtkinter.CTkLabel(
                    self.background, text="Starting download...")
                self.download_status_label.pack(padx=5, pady=(0, 5))
                self.add_output("Downloading new release...\n\n")

                # Download with progress update
                with open(os.path.join(download_path, f"{self.name}.zip"), 'wb') as f:
                    start_time = time.time()

                    for data in response.iter_content(chunk_size=4096):
                        downloaded += len(data)
                        f.write(data)
                        elapsed_time = time.time() - start_time
                        download_speed = self.format_speed(
                            downloaded, elapsed_time)
                        self.progress_bar.set(downloaded / total_length)

                        # Update the download status label
                        downloaded_formatted = self.format_file_size(
                            downloaded)
                        total_length_formatted = self.format_file_size(
                            total_length)
                        download_status_text = f"{downloaded_formatted} of {total_length_formatted}, {downloaded / total_length * 100:.2f}% ({download_speed})"
                        self.download_status_label.configure(
                            text=download_status_text)

                        # Update the UI to reflect progress
                        self.background.update_idletasks()

            # log successful download of new .zip
            self.add_output(f"Downloaded update to:\n{download_path}\n\n")
            time.sleep(0.5)

        except (KeyError, IndexError, requests.exceptions.RequestException) as e:
            self.add_output(
                f"Error during download: {e}\n\nClosing setup in 5 sec...")
            time.sleep(5)
            self.destroy()

        # log creation of updater files
        self.add_output("Creating update handlers...\n\n")
        time.sleep(0.5)

        if os_name == "Windows":
            # create updater.ps1
            log_file_path = os.path.join(
                download_path, "update_log.txt")
            with open(os.path.join(download_path, "updater.ps1"), "w") as outfile:
                outfile.write(f"""function Log-Output {{
    Param ([string]$message)
    echo $message
    echo $message >> "{log_file_path}"
}}

$errorOccurred = $false

echo "Logging update process to {log_file_path}..."

Log-Output "Closing {self.name}.exe..."
Start-Sleep -Seconds 2
taskkill /F /IM "{self.name}.exe" /T >> "{log_file_path}" 2>&1

Log-Output "Copying {self.name}.exe from {download_path} to {os.path.join(os.path.dirname(sys.executable), f'{self.name}.zip')}..."
Start-Sleep -Seconds 1
Copy-Item -Path "{os.path.join(download_path, self.name + '.zip')}" -Destination "{os.path.join(os.path.dirname(sys.executable), self.name + '.zip')}" -Force >> "{log_file_path}" 2>&1
if (-not $?) {{ $errorOccurred = $true }}

Log-Output "Deleting old executable..."
Start-Sleep -Seconds 1
Remove-Item "{sys.executable}" >> "{log_file_path}" 2>&1
if (-not $?) {{ $errorOccurred = $true }}

Log-Output "Extracting {self.name}.zip..."
Start-Sleep -Seconds 1
Expand-Archive -Path "{os.path.join(os.path.dirname(sys.executable), self.name + '.zip')}" -DestinationPath "{os.path.dirname(sys.executable)}" -Force >> "{log_file_path}" 2>&1
if (-not $?) {{ $errorOccurred = $true }}

Log-Output "Deleting {self.name}.zip..."s
Start-Sleep -Seconds 1
Remove-Item "{os.path.join(os.path.dirname(sys.executable), self.name + '.zip')}" >> "{log_file_path}" 2>&1
if (-not $?) {{ $errorOccurred = $true }}

Log-Output "Launching {self.name}.exe..."
Start-Sleep -Seconds 3
start "{sys.executable}" >> "{log_file_path}" 2>&1
if (-not $?) {{ $errorOccurred = $true }}

Log-Output "Update finished!"
Log-Output "You can close this window now."

if ($errorOccurred) {{
    explorer.exe /select,"{log_file_path}"
}}
""")
            outfile.close()

            # log successful creation of updater.ps1
            self.add_output("updater.ps1 successfully created!\n\n")
            time.sleep(0.5)

            # create updater.bat
            with open(os.path.join(download_path, "updater.bat"), "w") as outfile:
                outfile.write(
                    f"""PowerShell -File "{os.path.join(download_path, "updater.ps1")}"\nexit""")
                outfile.close()

            # log successful creation of updater.bat
            self.add_output("updater.bat successfully created!\n\n")
            time.sleep(0.5)

            # log update start in 5 sek
            self.add_output("Starting update in 5 seconds!\n\n")
            time.sleep(0.5)

            # log estimated time
            self.add_output("Estimated update time: 10-15 sec.\n\n")
            time.sleep(2.5)

            # launch update
            subprocess.Popen(
                f"""start cmd /k "{os.path.join(download_path, 'updater.bat')}" """, shell=True)
            self.destroy()

        elif os_name == "Darwin":
            # create updater.sh
            log_file_path = os.path.join(
                download_path, "update_log.txt")  # Define log file path
            with open(os.path.join(download_path, "updater.sh"), "w") as outfile:
                outfile.write(f"""#!/bin/bash
log_file="{log_file_path}"
error_occurred=0

echo "Logging update process to ${{log_file}}..." | tee -a "${{log_file}}"

echo "Closing {self.name}..." | tee -a "${{log_file}}"
sleep 2
osascript -e 'quit app "{self.name}"' >> "${{log_file}}" 2>&1

echo "Removing old version..." | tee -a "${{log_file}}"
sleep 1
rm -rf "{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))), f'{self.name}.app')}" >> "${{log_file}}" 2>&1
if [ $? -ne 0 ]; then error_occurred=1; fi

echo "Extracting new version from {self.name}.zip to {os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))}..." | tee -a "${{log_file}}"
sleep 1
unzip -o "{os.path.join(download_path, f'{self.name}.zip')}" -d "{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))}" >> "${{log_file}}" 2>&1
if [ $? -ne 0 ]; then error_occurred=1; fi

echo "Deleting {self.name}.zip..." | tee -a "${{log_file}}"
sleep 1
rm "{os.path.join(download_path, f'{self.name}.zip')}" >> "${{log_file}}" 2>&1
if [ $? -ne 0 ]; then error_occurred=1; fi

echo "Launching {self.name}.app..." | tee -a "${{log_file}}"
sleep 3
open "{os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))), f'{self.name}.app')}" >> "${{log_file}}" 2>&1
if [ $? -ne 0 ]; then error_occurred=1; fi

if [ $error_occurred -ne 0 ]; then
    echo "An error occurred during the update process. Please check the log file for more details." | tee -a "${{log_file}}"
    open -R "{log_file_path}"
fi

echo "" | tee -a "${{log_file}}"
echo "Update finished!" | tee -a "${{log_file}}"
echo "You can close this window now." | tee -a "${{log_file}}"
exit""")
                outfile.close()

            # log successful creation of updater.sh
            self.add_output("updater.sh successfully created!\n\n")
            time.sleep(0.5)

            # log update start in 5 sek
            self.add_output("Starting update in 5 seconds!\n\n")
            time.sleep(0.5)

            # log estimated time
            self.add_output("Estimated update time: 10-15 sec.\n\n")
            time.sleep(2.5)

            # launch update
            subprocess.Popen(["sh", os.path.join(download_path, "updater.sh")])

            self.destroy()

        else:
            self.add_output(
                f"Unsupported OS detected ({os_name}). Please update manually.\n\nClosing setup in 5 sec...")
            time.sleep(5)
            self.destroy()
