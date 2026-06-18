"""Toplevel that offers a one-click self-update."""

from __future__ import annotations

import logging
import os
import threading
import webbrowser
from collections.abc import Callable

import customtkinter

from .. import updater
from ..updater import UpdateInfo

logger = logging.getLogger("yt_downloader")


class UpdateDialog(customtkinter.CTkToplevel):
    def __init__(
        self, parent, info: UpdateInfo, on_apply: Callable[[], None] | None = None
    ) -> None:
        super().__init__(parent)
        self._info = info
        self._on_apply = on_apply

        self.title("Update available")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.geometry("400x200")

        self._frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self._frame.pack(fill="both", expand=True, padx=20, pady=20)

        customtkinter.CTkLabel(
            self._frame,
            text="A new version is available",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        ).pack(pady=(4, 6))
        customtkinter.CTkLabel(
            self._frame,
            text=f"Current  v{info.current}      Latest  v{info.latest}",
            text_color=("gray40", "gray60"),
        ).pack(pady=(0, 14))

        self._buttons = customtkinter.CTkFrame(self._frame, fg_color="transparent")
        self._buttons.pack()
        customtkinter.CTkButton(
            self._buttons, text="Later", width=110, command=self.destroy,
            fg_color="transparent", border_width=1,
            border_color=("gray72", "gray34"), text_color=("gray25", "#C0C4C8"),
            hover_color=("gray82", "gray26"),
        ).grid(row=0, column=0, padx=6)
        customtkinter.CTkButton(
            self._buttons, text="Update now", width=130, command=self._start
        ).grid(row=0, column=1, padx=6)

    def _start(self) -> None:
        # No build for this OS, or running from source: just open the releases page.
        if not self._info.download_url or not updater.can_self_update():
            webbrowser.open(updater.RELEASES_PAGE)
            self.destroy()
            return

        self._buttons.destroy()
        self._progress = customtkinter.CTkProgressBar(self._frame)
        self._progress.set(0)
        self._progress.pack(fill="x", pady=(6, 6))
        self._status = customtkinter.CTkLabel(
            self._frame, text="Starting download...", text_color=("gray40", "gray60")
        )
        self._status.pack()
        threading.Thread(target=self._download, daemon=True).start()

    def _download(self) -> None:
        try:
            dest = os.path.join(updater.update_dir(self._info.latest), f"{updater.APP_NAME}.zip")
            updater.download_asset(
                self._info.download_url,
                dest,
                progress_cb=lambda done, total: self.after(
                    0, self._set_progress, done, total
                ),
            )
            self.after(0, self._apply, dest)
        except Exception as error:  # noqa: BLE001 - surface any failure in the dialog
            logger.error(f"[Update] Download failed: {error}")
            self.after(0, self._fail)

    def _set_progress(self, done: int, total: int) -> None:
        if total:
            self._progress.set(done / total)
            self._status.configure(text=f"{self._mb(done)} / {self._mb(total)} MB")
        else:
            self._status.configure(text=f"{self._mb(done)} MB")

    def _apply(self, zip_path: str) -> None:
        self._status.configure(text="Installing - the app will restart...")
        updater.apply_update(zip_path)
        if self._on_apply:
            self._on_apply()

    def _fail(self) -> None:
        self._status.configure(
            text="Update failed. Opening the releases page...", text_color="#E5484D"
        )
        webbrowser.open(updater.RELEASES_PAGE)

    @staticmethod
    def _mb(num_bytes: int) -> str:
        return f"{num_bytes / 1024 / 1024:.1f}"
