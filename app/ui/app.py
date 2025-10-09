"""PySide6 application entry-point for the requisitions UI."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Sequence

from PySide6.QtCore import QCoreApplication, QLibraryInfo
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def _ensure_qt_plugin_path() -> None:
    """Ensure the Qt platform plugins directory is discoverable.

    Some macOS environments fail to locate the ``cocoa`` platform plugin on
    subsequent launches when the library path cache is lost. We add the
    runtime plugin directory exposed by ``QLibraryInfo`` to both Qt's internal
    library search paths and the conventional environment variables so that the
    platform plugin remains available even after restarting the application.
    """

    plugin_dir = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    if not plugin_dir.exists():  # Defensive: nothing to do if path unavailable
        return

    existing_paths = {Path(p) for p in QCoreApplication.libraryPaths()}
    if plugin_dir not in existing_paths:
        QCoreApplication.addLibraryPath(str(plugin_dir))

    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugin_dir))
    os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_dir))


def run(argv: Sequence[str] | None = None) -> int:
    """Start the Qt application.

    Parameters
    ----------
    argv:
        Optional sequence of command line arguments. Only used to initialise the
        QApplication instance. Defaults to ``sys.argv`` when ``None``.
    """

    _ensure_qt_plugin_path()

    app = QApplication(list(argv) if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    raise SystemExit(main())
