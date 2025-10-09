"""Splash screen with transparent background awaiting user interaction."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel


class SplashScreen(QDialog):
    """Simple splash screen that closes when the user clicks it."""

    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.setObjectName("splash-screen")
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        pixmap = QPixmap(str(Path(__file__).with_name("bwb-Splash.png")))
        self._label = QLabel(self)
        self._label.setObjectName("splash-image")
        self._label.setPixmap(pixmap)
        self._label.setScaledContents(True)
        self._label.setAttribute(Qt.WA_TranslucentBackground, True)

        if not pixmap.isNull():
            self.setFixedSize(pixmap.size())
        else:
            # Fallback size when the image fails to load.
            self.setFixedSize(800, 500)

        self._label.resize(self.size())

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
