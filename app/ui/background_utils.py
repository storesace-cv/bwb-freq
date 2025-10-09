"""Utilities for managing transparent backgrounds in Qt widgets."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QPalette, QPixmap
from PySide6.QtWidgets import QLabel, QWidget


def ensure_transparent(widget: QWidget) -> None:
    """Apply the attributes required for a fully transparent widget."""

    widget.setAttribute(Qt.WA_TranslucentBackground, True)
    widget.setAttribute(Qt.WA_NoSystemBackground, True)
    widget.setAttribute(Qt.WA_OpaquePaintEvent, False)
    widget.setAttribute(Qt.WA_StyledBackground, True)
    widget.setAutoFillBackground(False)

    palette = widget.palette()
    palette.setColor(QPalette.Window, Qt.transparent)
    palette.setColor(QPalette.Base, Qt.transparent)
    palette.setColor(QPalette.Button, Qt.transparent)
    widget.setPalette(palette)

    stylesheet = widget.styleSheet().strip()
    transparent_rule = "background-color: rgba(0, 0, 0, 0);"
    if transparent_rule not in stylesheet:
        if stylesheet:
            if not stylesheet.rstrip().endswith(";"):
                stylesheet = f"{stylesheet};"
            stylesheet = f"{stylesheet}\n{transparent_rule}"
        else:
            stylesheet = transparent_rule
        widget.setStyleSheet(stylesheet)


class BackgroundLayer(QObject):
    """Keep a QLabel sized to its host to display a background pixmap."""

    def __init__(self, host: QWidget, image_path: Path, object_name: str = "background-layer") -> None:
        super().__init__(host)
        self.host = host
        self.image_path = image_path
        self.object_name = object_name

        self._label = QLabel(self.host)
        self._label.setObjectName(self.object_name)
        self._label.setAttribute(Qt.WA_TranslucentBackground, True)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._label.setStyleSheet("background: transparent;")

        pixmap = QPixmap(str(self.image_path))
        self._label.setPixmap(pixmap)
        self._label.setScaledContents(True)
        self._label.lower()

        self.host.installEventFilter(self)
        self._sync_to_host()

    @property
    def label(self) -> QLabel:
        """Expose the internal QLabel for additional customisation."""

        return self._label

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if obj is self.host and event.type() in {QEvent.Resize, QEvent.Show}:
            self._sync_to_host()
        return super().eventFilter(obj, event)

    def _sync_to_host(self) -> None:
        self._label.resize(self.host.size())

