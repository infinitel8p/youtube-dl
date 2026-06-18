"""The main window. The only place Tk widgets get touched - workers talk via the queue."""

from __future__ import annotations

import contextlib
import io
import logging
import os
import queue
import sys
import threading
import urllib.request

import customtkinter
from PIL import Image

from .. import __version__, updater
from ..downloader import DownloadManager, Metadata, fetch_metadata, fetch_title, format_duration
from ..events import Event, Failed, Finished, LogMessage, Progress, Stage
from ..formats import DEFAULT_FORMAT, extensions, quality_choices
from ..resources import resource_path
from ..theming import DEFAULT_THEME, available_themes, theme_path
from .log_handler import QueueLogHandler
from .update_dialog import UpdateDialog

logger = logging.getLogger("yt_downloader")

_PUMP_INTERVAL_MS = 100
_PREVIEW_DEBOUNCE_MS = 700
_PAD = 20

# Layout rows for the main window grid (top to bottom).
_ROW_HEADER = 0
_ROW_INPUT = 1
_ROW_PREVIEW = 2
_ROW_STATUS = 3
_ROW_PROGRESS = 4
_ROW_LOG_HEADER = 5
_ROW_LOG = 6

_THUMB_SIZE = (120, 68)

# (light, dark) pairs so they read in either appearance mode
_STATUS_COLORS = {
    "idle": ("gray45", "gray55"),
    "working": ("#2563EB", "#5B9BF6"),
    "success": ("#15803D", "#3DD68C"),
    "error": ("#C93C41", "#FF6B6B"),
}

# info is left out on purpose so it keeps the theme's text colour
_LOG_COLORS = {
    "error": "#E5484D",
    "warning": "#C2710C",
    "debug": "#8A8F94",
}


def _download_image(url: str, *, timeout: float = 8.0, max_bytes: int = 5_000_000) -> bytes | None:
    """Fetch thumbnail bytes off the main thread. Never raises."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - http(s) thumbnail
            return response.read(max_bytes)
    except Exception:  # noqa: BLE001 - a failed thumbnail just means no image
        return None


class MainWindow(customtkinter.CTk):
    """The YouTube Downloader main window."""

    def __init__(self) -> None:
        super().__init__()

        self._events: queue.Queue[Event] = queue.Queue()
        self._manager = DownloadManager(self._events)
        self._busy = False
        self._progress_visible = False
        self._indeterminate = False
        self._quality_token_by_label: dict[str, str] = {}

        self._status_text = "Ready"
        self._status_kind = "idle"

        # theme picker state
        self._current_theme = DEFAULT_THEME
        self._appearance_value = "System"
        self._theme_choices = available_themes()
        self._theme_stem_by_label = {label: stem for label, stem in self._theme_choices}
        self._theme_label_by_stem = {stem: label for label, stem in self._theme_choices}

        # preview state
        self._preview_metadata: Metadata | None = None
        self._preview_pil_image: Image.Image | None = None
        self._preview_thumb_image: customtkinter.CTkImage | None = None
        self._preview_request = 0
        self._preview_after_id: str | None = None
        self._last_preview_url: str | None = None

        self._configure_logging()
        self._configure_window()
        self._build_fonts()
        self._build_widgets()
        self._on_format_change(DEFAULT_FORMAT)
        self._update_download_state()
        self._hide_progress()
        self._set_status("Ready", "idle")

        logger.info(f"YouTube Downloader v{__version__} ready.")
        self.after(_PUMP_INTERVAL_MS, self._pump_events)
        self.after(900, self._begin_update_check)

    # -- setup ---------------------------------------------------------------

    def _configure_logging(self) -> None:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(QueueLogHandler(self._events))

    def _configure_window(self) -> None:
        self.title("YouTube Downloader")
        customtkinter.set_appearance_mode(self._appearance_value.lower())
        customtkinter.set_default_color_theme(theme_path(self._current_theme))
        self.geometry("480x680")
        self.minsize(440, 600)

        self._icon_image: customtkinter.CTkImage | None = None
        icon_path = resource_path("config", "icon.ico")
        if os.path.exists(icon_path):
            try:
                image = Image.open(icon_path)
                self._icon_image = customtkinter.CTkImage(image, size=(44, 44))
            except Exception:  # noqa: BLE001 - a missing/broken icon must not crash startup
                self._icon_image = None
            if self._icon_image is not None and sys.platform.startswith("win"):
                with contextlib.suppress(Exception):
                    self.iconbitmap(icon_path)

    def _build_fonts(self) -> None:
        self._font_title = customtkinter.CTkFont(size=21, weight="bold")
        self._font_subtitle = customtkinter.CTkFont(size=11)
        self._font_section = customtkinter.CTkFont(size=12, weight="bold")
        self._font_button = customtkinter.CTkFont(size=14, weight="bold")
        self._font_status = customtkinter.CTkFont(size=12)
        self._font_preview_title = customtkinter.CTkFont(size=13, weight="bold")
        mono = {"darwin": "Menlo", "win32": "Consolas"}.get(sys.platform, "monospace")
        self._font_log = customtkinter.CTkFont(family=mono, size=11)

    def _build_widgets(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(_ROW_LOG, weight=1)

        self._build_header()
        self._build_input_card()
        self._build_preview()
        self._build_status_row()
        self._build_progress()
        self._build_log_header()
        self._build_log()

    def _build_header(self) -> None:
        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.grid(row=_ROW_HEADER, column=0, sticky="ew", padx=_PAD, pady=(18, 8))
        header.grid_columnconfigure(1, weight=1)

        if self._icon_image is not None:
            icon = customtkinter.CTkLabel(header, text="", image=self._icon_image)
            icon.grid(row=0, column=0, rowspan=2, padx=(0, 12))

        title = customtkinter.CTkLabel(
            header, text="YouTube Downloader", font=self._font_title, anchor="w"
        )
        title.grid(row=0, column=1, sticky="sw")
        subtitle = customtkinter.CTkLabel(
            header,
            text="Save video & audio from YouTube and more",
            font=self._font_subtitle,
            text_color=("gray45", "gray55"),
            anchor="w",
        )
        subtitle.grid(row=1, column=1, sticky="nw")

        controls = customtkinter.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=2, rowspan=2, sticky="e")

        self._appearance = customtkinter.CTkSegmentedButton(
            controls,
            values=["Light", "Dark", "System"],
            command=self._on_appearance_change,
            font=self._font_subtitle,
            width=180,
        )
        self._appearance.set(self._appearance_value)
        self._appearance.grid(row=0, column=0, sticky="e")

        self._theme_menu = customtkinter.CTkOptionMenu(
            controls,
            values=[label for label, _ in self._theme_choices],
            command=self._on_theme_change,
            font=self._font_subtitle,
            width=180,
        )
        self._theme_menu.set(self._theme_label_by_stem.get(self._current_theme, "Polished"))
        self._theme_menu.grid(row=1, column=0, sticky="e", pady=(8, 0))

    def _build_input_card(self) -> None:
        card = customtkinter.CTkFrame(
            self, border_width=1, border_color=("gray82", "gray24")
        )
        card.grid(row=_ROW_INPUT, column=0, sticky="ew", padx=_PAD, pady=(4, 6))
        card.grid_columnconfigure(0, weight=1)

        link_label = customtkinter.CTkLabel(
            card, text="VIDEO OR PLAYLIST LINK", font=self._font_section,
            text_color=("gray40", "gray60"), anchor="w",
        )
        link_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        entry_row = customtkinter.CTkFrame(card, fg_color="transparent")
        entry_row.grid(row=1, column=0, sticky="ew", padx=16)
        entry_row.grid_columnconfigure(0, weight=1)

        self._url_input = customtkinter.CTkEntry(
            entry_row, placeholder_text="https://...", height=38
        )
        self._url_input.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._url_input.bind("<Return>", lambda _event: self.start_download())
        self._url_input.bind("<KeyRelease>", lambda _event: self._on_url_changed())

        paste_button = self._make_secondary_button(
            entry_row, text="Paste", command=self._paste_from_clipboard, width=72, height=38
        )
        paste_button.grid(row=0, column=1)

        controls = customtkinter.CTkFrame(card, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=16, pady=(12, 2))
        controls.grid_columnconfigure(2, weight=1)

        self._format_menu = customtkinter.CTkOptionMenu(
            controls, width=104, values=extensions(), command=self._on_format_change,
            font=self._font_subtitle,
        )
        self._format_menu.set(DEFAULT_FORMAT)
        self._format_menu.grid(row=0, column=0, padx=(0, 8))

        self._quality_menu = customtkinter.CTkOptionMenu(
            controls, width=140, values=["Best available"], font=self._font_subtitle,
        )
        self._quality_menu.grid(row=0, column=1, sticky="w")

        switches = customtkinter.CTkFrame(controls, fg_color="transparent")
        switches.grid(row=1, column=0, columnspan=3, sticky="w", pady=(12, 2))
        self._playlist_switch = customtkinter.CTkSwitch(
            switches, text="Playlist", font=self._font_subtitle
        )
        self._playlist_switch.grid(row=0, column=0, padx=(0, 20))
        self._subtitles_switch = customtkinter.CTkSwitch(
            switches, text="Subtitles", font=self._font_subtitle
        )
        self._subtitles_switch.grid(row=0, column=1)

        self._download_button = customtkinter.CTkButton(
            card, text="Download", command=self.start_download, height=44,
            font=self._font_button,
        )
        self._download_button.grid(row=3, column=0, sticky="ew", padx=16, pady=(14, 16))

    def _build_preview(self) -> None:
        card = customtkinter.CTkFrame(self, border_width=1, border_color=("gray82", "gray24"))
        card.grid(row=_ROW_PREVIEW, column=0, sticky="ew", padx=_PAD, pady=(2, 6))
        card.grid_columnconfigure(1, weight=1)
        self._preview_card = card

        self._preview_thumb = customtkinter.CTkLabel(
            card, text="", width=_THUMB_SIZE[0], height=_THUMB_SIZE[1],
            fg_color=("gray88", "gray22"), corner_radius=6,
        )
        self._preview_thumb.grid(row=0, column=0, rowspan=2, padx=12, pady=12)

        self._preview_title = customtkinter.CTkLabel(
            card, text="", font=self._font_preview_title, anchor="w", justify="left",
            wraplength=270,
        )
        self._preview_title.grid(row=0, column=1, sticky="sw", padx=(0, 14), pady=(14, 0))

        self._preview_meta = customtkinter.CTkLabel(
            card, text="", font=self._font_subtitle, text_color=("gray40", "gray60"),
            anchor="w",
        )
        self._preview_meta.grid(row=1, column=1, sticky="nw", padx=(0, 14), pady=(2, 14))

        card.grid_remove()

    def _build_status_row(self) -> None:
        row = customtkinter.CTkFrame(self, fg_color="transparent")
        row.grid(row=_ROW_STATUS, column=0, sticky="ew", padx=_PAD + 4, pady=(4, 0))
        row.grid_columnconfigure(0, weight=1)
        self._status_label = customtkinter.CTkLabel(
            row, text="", font=self._font_status, anchor="w"
        )
        self._status_label.grid(row=0, column=0, sticky="w")

    def _build_progress(self) -> None:
        self._progress_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self._progress_frame.grid(
            row=_ROW_PROGRESS, column=0, sticky="ew", padx=_PAD + 4, pady=(4, 4)
        )
        self._progress_frame.grid_columnconfigure(0, weight=1)

        self._progress_bar = customtkinter.CTkProgressBar(
            self._progress_frame, mode="determinate", height=8
        )
        self._progress_bar.grid(row=0, column=0, sticky="ew")
        self._progress_bar.set(0)

        self._progress_detail = customtkinter.CTkLabel(
            self._progress_frame, text="", font=self._font_subtitle,
            text_color=("gray40", "gray60"), anchor="w",
        )
        self._progress_detail.grid(row=1, column=0, sticky="w", pady=(5, 0))

    def _build_log_header(self) -> None:
        row = customtkinter.CTkFrame(self, fg_color="transparent")
        row.grid(row=_ROW_LOG_HEADER, column=0, sticky="ew", padx=_PAD + 4, pady=(8, 4))
        row.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(
            row, text="ACTIVITY", font=self._font_section,
            text_color=("gray40", "gray60"), anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self._make_secondary_button(
            row, text="Clear", command=self._clear_log, width=60, height=26
        ).grid(row=0, column=1, sticky="e")

    def _build_log(self) -> None:
        self._log_output = customtkinter.CTkTextbox(
            self, state="disabled", font=self._font_log, wrap="word",
            border_width=1, border_color=("gray82", "gray24"),
        )
        self._log_output.grid(row=_ROW_LOG, column=0, sticky="nsew", padx=_PAD, pady=(0, 18))
        textbox = getattr(self._log_output, "_textbox", None)
        if textbox is not None:
            for level, color in _LOG_COLORS.items():
                textbox.tag_config(level, foreground=color)

    def _make_secondary_button(self, master, **kwargs) -> customtkinter.CTkButton:
        """Create a subtle, outlined button (for non-primary actions)."""
        return customtkinter.CTkButton(
            master,
            fg_color="transparent",
            hover_color=("gray82", "gray26"),
            text_color=("gray25", "#C0C4C8"),
            border_width=1,
            border_color=("gray72", "gray34"),
            font=self._font_subtitle,
            **kwargs,
        )

    # -- event pump ----------------------------------------------------------

    def _pump_events(self) -> None:
        """Drain the event queue and apply updates on the main thread."""
        try:
            while True:
                self._handle_event(self._events.get_nowait())
        except queue.Empty:
            pass
        self.after(_PUMP_INTERVAL_MS, self._pump_events)

    def _handle_event(self, event: Event) -> None:
        if isinstance(event, LogMessage):
            self._append_log(event.text, event.level)
        elif isinstance(event, Stage):
            self._set_status(event.text, "working")
        elif isinstance(event, Progress):
            self._apply_progress(event)
        elif isinstance(event, Finished):
            self._finish_success()
        elif isinstance(event, Failed):
            self._finish_failure()

    # -- status & progress ---------------------------------------------------

    def _set_status(self, text: str, kind: str) -> None:
        self._status_text = text
        self._status_kind = kind
        self._status_label.configure(
            text=f"●  {text}", text_color=_STATUS_COLORS.get(kind, _STATUS_COLORS["idle"])
        )

    def _show_progress(self) -> None:
        if not self._progress_visible:
            self._progress_frame.grid()
            self._progress_visible = True

    def _hide_progress(self) -> None:
        if self._indeterminate:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate")
            self._indeterminate = False
        self._progress_bar.set(0)
        self._progress_detail.configure(text="")
        self._progress_frame.grid_remove()
        self._progress_visible = False

    def _apply_progress(self, event: Progress) -> None:
        self._show_progress()
        if event.fraction is None:
            if not self._indeterminate:
                self._progress_bar.configure(mode="indeterminate")
                self._progress_bar.start()
                self._indeterminate = True
            percent = ""
        else:
            if self._indeterminate:
                self._progress_bar.stop()
                self._progress_bar.configure(mode="determinate")
                self._indeterminate = False
            self._progress_bar.set(event.fraction)
            percent = f"{int(event.fraction * 100)}%"

        parts = [
            piece
            for piece in (percent, self._format_speed(event.speed), self._format_eta(event.eta))
            if piece
        ]
        self._progress_detail.configure(text="   ·   ".join(parts) or "Working...")

    def _finish_success(self) -> None:
        if self._indeterminate:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate")
            self._indeterminate = False
        self._progress_bar.set(1.0)
        self._progress_detail.configure(text="100%")
        self._set_status("Done", "success")
        self._set_busy(False)
        self.after(2200, self._reset_idle)

    def _finish_failure(self) -> None:
        self._hide_progress()
        self._set_status("Download failed - see activity log", "error")
        self._set_busy(False)

    def _reset_idle(self) -> None:
        if not self._busy:
            self._hide_progress()
            self._set_status("Ready", "idle")

    # -- log -----------------------------------------------------------------

    def _append_log(self, text: str, level: str) -> None:
        self._log_output.configure(state="normal")
        tag = level if level in _LOG_COLORS else None
        self._log_output.insert(customtkinter.END, text + "\n", tag)
        self._log_output.see(customtkinter.END)
        self._log_output.configure(state="disabled")

    def _clear_log(self) -> None:
        self._log_output.configure(state="normal")
        self._log_output.delete("1.0", customtkinter.END)
        self._log_output.configure(state="disabled")

    def _log_text(self) -> str:
        return self._log_output.get("1.0", "end-1c")

    def _restore_log(self, text: str) -> None:
        if not text:
            return
        self._log_output.configure(state="normal")
        self._log_output.insert(customtkinter.END, text)
        self._log_output.see(customtkinter.END)
        self._log_output.configure(state="disabled")

    # -- input state ---------------------------------------------------------

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_download_state()

    def _update_download_state(self) -> None:
        has_url = bool(self._url_input.get().strip())
        enabled = has_url and not self._busy
        self._download_button.configure(
            state=customtkinter.NORMAL if enabled else customtkinter.DISABLED
        )

    def _on_url_changed(self) -> None:
        self._update_download_state()
        self._schedule_preview()

    def _on_format_change(self, extension: str) -> None:
        choices = quality_choices(extension)
        self._quality_token_by_label = {label: token for label, token in choices}
        labels = [label for label, _ in choices]
        self._quality_menu.configure(values=labels)
        self._quality_menu.set(labels[0])

    def _on_appearance_change(self, mode: str) -> None:
        self._appearance_value = mode
        customtkinter.set_appearance_mode(mode.lower())

    def _paste_from_clipboard(self) -> None:
        try:
            text = self.clipboard_get()
        except Exception:  # noqa: BLE001 - empty/non-text clipboard
            return
        self._url_input.delete(0, customtkinter.END)
        self._url_input.insert(0, text.strip())
        self._on_url_changed()

    def _current_quality(self) -> str:
        return self._quality_token_by_label.get(self._quality_menu.get(), "best")

    # -- theme picker --------------------------------------------------------

    def _on_theme_change(self, label: str) -> None:
        stem = self._theme_stem_by_label.get(label)
        if not stem or stem == self._current_theme:
            return
        self._current_theme = stem
        self._rebuild_for_theme()

    def _rebuild_for_theme(self) -> None:
        """customtkinter can't restyle live widgets, so tear down and rebuild in place."""
        state = self._snapshot_state()
        customtkinter.set_default_color_theme(theme_path(self._current_theme))
        for child in self.winfo_children():
            child.destroy()
        self._progress_visible = False
        self._indeterminate = False
        self._build_fonts()
        self._build_widgets()
        self._restore_state(state)

    def _snapshot_state(self) -> dict:
        return {
            "url": self._url_input.get(),
            "format": self._format_menu.get(),
            "quality": self._quality_menu.get(),
            "playlist": self._playlist_switch.get(),
            "subtitles": self._subtitles_switch.get(),
            "log": self._log_text(),
            "status_text": self._status_text,
            "status_kind": self._status_kind,
            "busy": self._busy,
        }

    def _restore_state(self, state: dict) -> None:
        self._url_input.insert(0, state["url"])
        self._format_menu.set(state["format"])
        self._on_format_change(state["format"])
        if state["quality"] in self._quality_token_by_label:
            self._quality_menu.set(state["quality"])
        if state["playlist"]:
            self._playlist_switch.select()
        if state["subtitles"]:
            self._subtitles_switch.select()
        self._theme_menu.set(self._theme_label_by_stem.get(self._current_theme, "Polished"))
        self._appearance.set(self._appearance_value)

        self._restore_log(state["log"])
        if self._preview_metadata is not None:
            self._render_preview()
        else:
            self._hide_preview()

        self._busy = state["busy"]
        self._update_download_state()
        self._hide_progress()
        self._set_status(state["status_text"], state["status_kind"])

    # -- preview -------------------------------------------------------------

    @staticmethod
    def _looks_like_url(text: str) -> bool:
        return text.startswith(("http://", "https://")) and "." in text

    def _schedule_preview(self) -> None:
        if self._preview_after_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(_PREVIEW_DEBOUNCE_MS, self._request_preview)

    def _request_preview(self) -> None:
        self._preview_after_id = None
        url = self._url_input.get().strip()
        if not self._looks_like_url(url):
            self._last_preview_url = None
            self._hide_preview()
            return
        if url == self._last_preview_url:
            return
        self._last_preview_url = url
        self._preview_request += 1
        token = self._preview_request
        self._set_preview_loading()
        threading.Thread(
            target=self._preview_worker, args=(url, token), daemon=True
        ).start()

    def _preview_worker(self, url: str, token: int) -> None:
        metadata = fetch_metadata(url)
        image_bytes = None
        if metadata is not None and metadata.thumbnail_url:
            image_bytes = _download_image(metadata.thumbnail_url)
        self.after(0, lambda: self._apply_preview(token, metadata, image_bytes))

    def _apply_preview(
        self, token: int, metadata: Metadata | None, image_bytes: bytes | None
    ) -> None:
        if token != self._preview_request:
            return  # a newer request superseded this one
        if metadata is None:
            self._hide_preview()
            return
        pil_image: Image.Image | None = None
        if image_bytes:
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
            except Exception:  # noqa: BLE001 - a broken image just means no thumbnail
                pil_image = None
        self._preview_metadata = metadata
        self._preview_pil_image = pil_image
        self._render_preview()

    def _render_preview(self) -> None:
        metadata = self._preview_metadata
        if metadata is None:
            return
        if self._preview_pil_image is not None:
            self._preview_thumb_image = customtkinter.CTkImage(
                self._preview_pil_image, size=_THUMB_SIZE
            )
            self._preview_thumb.configure(image=self._preview_thumb_image, text="")
        else:
            self._preview_thumb_image = None
            self._preview_thumb.configure(image=None, text="No preview")
        self._preview_title.configure(text=metadata.title)
        meta_parts = [
            part for part in (metadata.uploader, format_duration(metadata.duration)) if part
        ]
        self._preview_meta.configure(text="   ·   ".join(meta_parts))
        self._preview_card.grid()

    def _set_preview_loading(self) -> None:
        self._preview_thumb_image = None
        self._preview_thumb.configure(image=None, text="")
        self._preview_title.configure(text="Fetching preview...")
        self._preview_meta.configure(text="")
        self._preview_card.grid()

    def _hide_preview(self) -> None:
        self._preview_metadata = None
        self._preview_pil_image = None
        self._preview_thumb_image = None
        self._preview_card.grid_remove()

    # -- actions -------------------------------------------------------------

    def start_download(self) -> None:
        """Validate input and begin the download flow."""
        if self._manager.is_running:
            logger.warning("[Warning] A download is already in progress.")
            return

        url = self._url_input.get().strip()
        if not url:
            logger.warning("[Warning] Please enter a video link first.")
            return

        self._set_busy(True)
        self._set_status("Preparing...", "working")

        if self._playlist_switch.get() == 1:
            logger.info("[Info] Downloading playlist.")
            from tkinter import filedialog

            download_dir = filedialog.askdirectory()
            if not download_dir:
                logger.warning("[Warning] Download cancelled.")
                self._set_busy(False)
                self._set_status("Ready", "idle")
                return
            self._launch(url=url, download_dir=download_dir, filename=None)
        else:
            logger.info("[Info] Downloading single video.")
            self._set_status("Fetching video info...", "working")
            # fetch the title off-thread, then open the save dialog back on the main thread
            threading.Thread(
                target=self._fetch_title_then_prompt, args=(url,), daemon=True
            ).start()

    def _fetch_title_then_prompt(self, url: str) -> None:
        title = fetch_title(url)
        self.after(0, lambda: self._prompt_save_and_launch(url, title))

    def _prompt_save_and_launch(self, url: str, suggested_title: str) -> None:
        from tkinter import filedialog

        extension = self._format_menu.get()
        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{extension}",
            filetypes=[(f"{extension.upper()} files", f"*.{extension}")],
            initialfile=suggested_title,
        )
        if not file_path:
            logger.warning("[Warning] Download cancelled.")
            self._set_busy(False)
            self._set_status("Ready", "idle")
            return

        download_dir, name_with_ext = os.path.split(file_path)
        filename = os.path.splitext(name_with_ext)[0]
        self._launch(url=url, download_dir=download_dir, filename=filename)

    def _launch(self, *, url: str, download_dir: str, filename: str | None) -> None:
        started = self._manager.start(
            url=url,
            file_format=self._format_menu.get(),
            download_dir=download_dir,
            filename=filename,
            quality=self._current_quality(),
            subtitles=self._subtitles_switch.get() == 1,
        )
        if not started:
            self._set_busy(False)
            self._set_status("Ready", "idle")

    # -- updates -------------------------------------------------------------

    def _begin_update_check(self) -> None:
        def worker() -> None:
            info = updater.check_for_update(__version__)
            if info is not None:
                self.after(0, lambda: self._show_update(info))

        threading.Thread(target=worker, daemon=True).start()

    def _show_update(self, info: updater.UpdateInfo) -> None:
        logger.info(f"[Update] New version available: v{info.latest}")
        dialog = UpdateDialog(self, info, on_apply=self._quit_for_update)
        dialog.grab_set()

    def _quit_for_update(self) -> None:
        self.destroy()

    # -- formatting helpers --------------------------------------------------

    @staticmethod
    def _format_speed(speed: float | None) -> str:
        if not speed:
            return ""
        return f"{MainWindow._format_size(speed)}/s"

    @staticmethod
    def _format_size(num_bytes: float) -> str:
        size = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    @staticmethod
    def _format_eta(seconds: int | None) -> str:
        if seconds is None:
            return ""
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d} left"
        return f"{minutes:02d}:{secs:02d} left"
