"""wxPython application entry-point for the requisitions UI."""
from __future__ import annotations

import logging
import os
import sys

import wx

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
    _debug_log(f"wx.version={wx.version()}")
    relevant_vars = [
        "FREQ_DEBUGGER_LOG",
    ]
    for var in relevant_vars:
        value = os.environ.get(var)
        _debug_log(f"{var}={value}" if value is not None else f"{var}=<não definido>")


if DEBUGGER_LOGGER is not None:
    _debug_log("Módulo app.ui.app importado; ambiente de debug activo.")
    _log_environment_snapshot()


class FrequencyApp(wx.App):
    """wxPython application that bootstraps the requisitions UI."""

    def __init__(self) -> None:
        super().__init__(clearSigInt=True)
        self._main_window: MainWindow | None = None
        self._splash: SplashScreen | None = None

    def OnInit(self) -> bool:  # type: ignore[override]
        _debug_log("Inicialização da aplicação wxPython iniciada.")
        try:
            self._initialise_windows()
        except Exception:  # pragma: no cover - defensive UI bootstrap guard
            _debug_exception("Falha ao inicializar a interface wxPython")
            raise
        return True

    def _initialise_windows(self) -> None:
        self.SetAppDisplayName("Requisições Internas — MVP")

        main_window = MainWindow()
        self._main_window = main_window
        self.SetTopWindow(main_window)

        if APP_ICON.exists():
            try:
                icon = wx.Icon(str(APP_ICON))
            except Exception:  # pragma: no cover - icon loading issues
                icon = None
            if icon and icon.IsOk():
                main_window.SetIcon(icon)

        splash = SplashScreen(on_click=self._show_main_window)
        if splash.is_available:
            self._splash = splash
            splash.Show()
            main_window.Hide()
        else:
            self._show_main_window()

    def _show_main_window(self) -> None:
        if self._splash is not None:
            self._splash.Destroy()
            self._splash = None

        if self._main_window is not None:
            _debug_log("A abrir a janela principal.")
            self._main_window.Centre()
            self._main_window.Show()


def run() -> int:
    """Start the wxPython main loop."""

    app = FrequencyApp()
    app.MainLoop()
    return 0


def main() -> int:
    """Entry point compatible with ``python -m app.ui``."""

    try:
        return run()
    except Exception:  # pragma: no cover - ensure logging of unexpected failures
        _debug_exception("Erro fatal na aplicação wxPython")
        raise


__all__ = ["main", "run"]
