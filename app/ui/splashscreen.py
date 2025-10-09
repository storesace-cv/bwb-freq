"""Splash screen with transparent background awaiting user interaction."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel

from app.ui.background_utils import BackgroundLayer, ensure_transparent


class SplashScreen(QDialog):
    """Simple splash screen that closes when the user clicks it."""

    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("splash-screen")
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        ensure_transparent(self)

        background_path = Path(__file__).with_name("bwb-Splash-background.png")
        splash_path = Path(__file__).with_name("bwb-Splash.png")

        self._background_layer = BackgroundLayer(
            self, background_path, "splash-background"
        )

        pixmap = QPixmap(str(splash_path))
        self._label = QLabel(self)
        self._label.setObjectName("splash-image")
        self._label.setPixmap(pixmap)
        self._label.setScaledContents(True)
        self._label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._label.setStyleSheet("background: transparent;")

        background_pixmap = self._background_layer.label.pixmap()
        if background_pixmap is not None and not background_pixmap.isNull():
            self.setFixedSize(background_pixmap.size())
        elif not pixmap.isNull():
            self.setFixedSize(pixmap.size())
        else:
            # Fallback size when the image fails to load.
            self.setFixedSize(800, 500)

        self._label.resize(self.size())
        self._label.raise_()

    # ------------------------------------------------------------------
    # Qt event handlers
    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._label.resize(self.size())

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit()
        self.close()
        event.accept()
