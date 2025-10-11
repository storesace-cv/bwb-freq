"""Splash screen implemented with tkinter."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from app.ui.assets import BACKGROUND_IMAGE, SPLASH_IMAGE


class SplashScreen:
    """Simple splash screen that closes when the user clicks it."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_click: Callable[[], None],
        auto_dismiss_ms: int | None = 2500,
    ) -> None:
        self._master = master
        self._callback = on_click
        self._auto_job: str | None = None
        self._dismissed = False
        self._is_available = False

        window = tk.Toplevel(master)
        self._window = window
        window.withdraw()
        window.overrideredirect(True)
        try:
            window.attributes("-topmost", True)
        except tk.TclError:  # pragma: no cover - attribute unsupported
            pass

        container = ttk.Frame(window)
        container.pack(fill="both", expand=True)

        self._image_label = ttk.Label(container)
        self._image_label.pack(fill="both", expand=True)
        self._image_photo: ImageTk.PhotoImage | None = None

        if SPLASH_IMAGE.exists():
            self._image_photo = self._load_image(SPLASH_IMAGE)
        if self._image_photo is None and BACKGROUND_IMAGE.exists():
            self._image_photo = self._load_image(BACKGROUND_IMAGE)

        if self._image_photo is not None:
            self._image_label.configure(image=self._image_photo)
            window.geometry(
                f"{self._image_photo.width()}x{self._image_photo.height()}"
            )
            self._is_available = True
        else:
            window.geometry("800x500")
            self._is_available = True

        self._bind_events()

        if auto_dismiss_ms is not None and auto_dismiss_ms > 0:
            self._auto_job = window.after(auto_dismiss_ms, self._handle_timeout)

    @property
    def is_available(self) -> bool:
        return self._is_available

    def show(self) -> None:
        if not self._window.winfo_exists():
            return
        self._window.deiconify()
        self._center_on_screen()
        try:
            self._window.focus_force()
        except tk.TclError:
            pass

    def destroy(self) -> None:
        if self._window.winfo_exists():
            self._window.destroy()

    def _load_image(self, path: Path) -> ImageTk.PhotoImage | None:
        try:
            image = Image.open(path)
        except Exception:  # pragma: no cover - invalid/corrupt file
            return None
        width, height = image.size
        if width > 1200 or height > 900:
            ratio = min(1200 / width, 900 / height)
            image = image.resize((int(width * ratio), int(height * ratio)), Image.LANCZOS)
        return ImageTk.PhotoImage(image)

    def _center_on_screen(self) -> None:
        self._window.update_idletasks()
        width = self._window.winfo_width()
        height = self._window.winfo_height()
        screen_width = self._window.winfo_screenwidth()
        screen_height = self._window.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self._window.geometry(f"{width}x{height}+{x}+{y}")

    def _bind_events(self) -> None:
        widgets = [self._window, self._image_label]
        for widget in widgets:
            widget.bind("<ButtonRelease-1>", self._handle_click)
            widget.bind("<ButtonRelease-3>", self._handle_click)
            widget.bind("<KeyPress>", self._handle_key)

    def _handle_click(self, _event: tk.Event) -> None:
        self._invoke_callback()

    def _handle_key(self, event: tk.Event) -> None:
        if event.keysym in {"Escape", "Return", "space"}:
            self._invoke_callback()

    def _handle_timeout(self) -> None:
        self._invoke_callback()

    def _invoke_callback(self) -> None:
        if self._dismissed:
            return

        self._dismissed = True
        if self._auto_job is not None:
            try:
                self._window.after_cancel(self._auto_job)
            except tk.TclError:  # pragma: no cover - timer already cancelled
                pass
            self._auto_job = None
        self._window.withdraw()

        def _finalise() -> None:
            try:
                self._callback()
            finally:
                self.destroy()

        self._master.after(0, _finalise)
