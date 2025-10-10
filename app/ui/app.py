"""tkinter application entry-point for the requisitions UI."""
from __future__ import annotations

import logging
import os
import sys

import tkinter as tk

from app.ui.assets import APP_ICON
from app.ui.main_window import MainWindow
from app.ui.splashscreen import SplashScreen


def _setup_debug_logger() -> logging.Logger | None:
    """Initialise the shared file logger when debugging is enabled."""

    if os.environ.get("FREQ_DEBUGGER_ENABLED") != "1":
        return None
    log_path = os.environ.get("FREQ_DEBUGGER_LOG")
    if not log_path:
        return None

    logger = logging.getLogger("freq.debugger")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    try:
        handler = logging.FileHandler(log_path, encoding="utf-8")
    except OSError:
        return None

    formatter = logging.Formatter("%(asctime)s [app] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    logger.info("Logger de debug da aplicação inicializado em %s", log_path)
    return logger


DEBUGGER_LOGGER: logging.Logger | None = _setup_debug_logger()


def _debug_log(message: str, *, level: int = logging.INFO) -> None:
    if DEBUGGER_LOGGER is not None:
        DEBUGGER_LOGGER.log(level, message)


def _debug_exception(message: str) -> None:
    if DEBUGGER_LOGGER is not None:
        DEBUGGER_LOGGER.exception(message)


def _log_environment_snapshot() -> None:
    if DEBUGGER_LOGGER is None:
        return

    _debug_log(f"sys.executable={sys.executable}")
    _debug_log(f"sys.argv={sys.argv}")
    _debug_log(f"tkinter_version={tk.TkVersion}")
    relevant_vars = [
        "FREQ_DEBUGGER_LOG",
    ]
    for var in relevant_vars:
        value = os.environ.get(var)
        _debug_log(f"{var}={value}" if value is not None else f"{var}=<não definido>")


if DEBUGGER_LOGGER is not None:
    _debug_log("Módulo app.ui.app importado; ambiente de debug activo.")
    _log_environment_snapshot()


class FrequencyApp:
    """tkinter application that bootstraps the requisitions UI."""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.withdraw()
        self._main_window = MainWindow(self._root)
        self._splash: SplashScreen | None = None
        self._icon_image: tk.PhotoImage | None = None

        self._configure_icon()
        self._initialise_windows()

    def _configure_icon(self) -> None:
        if not APP_ICON.exists():
            return
        try:
            self._icon_image = tk.PhotoImage(file=str(APP_ICON))
        except Exception:  # pragma: no cover - invalid icon file
            self._icon_image = None
        if self._icon_image is not None:
            self._root.iconphoto(True, self._icon_image)

    def _initialise_windows(self) -> None:
        _debug_log("Inicialização da aplicação tkinter iniciada.")
        splash = SplashScreen(
            self._root, on_click=self._show_main_window, auto_dismiss_ms=3000
        )
        if splash.is_available:
            self._splash = splash
            splash.show()
        else:
            self._show_main_window()

    def _show_main_window(self) -> None:
        _debug_log("A abrir a janela principal.")
        self._root.deiconify()
        self._main_window.center_on_screen()
        self._root.lift()
        try:
            self._root.focus_force()
        except tk.TclError:
            pass

        splash = self._splash
        self._splash = None
        if splash is not None:
            splash.destroy()

    def run(self) -> None:
        self._root.mainloop()


def run() -> int:
    """Start the tkinter main loop."""

    app = FrequencyApp()
    app.run()
    return 0


def main() -> int:
    """Entry point compatible with ``python -m app.ui``."""

    try:
        return run()
    except Exception:  # pragma: no cover - ensure logging of unexpected failures
        _debug_exception("Erro fatal na aplicação tkinter")
        raise


__all__ = ["main", "run"]
