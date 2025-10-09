"""PySide6 application entry-point for the requisitions UI."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Iterable, Sequence

import PySide6
from PySide6.QtCore import QCoreApplication, QLibraryInfo
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def _dedupe_paths(paths: Iterable[str]) -> list[str]:
    """Return ``paths`` without duplicates while preserving order."""

    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if not path:
            continue
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def _candidate_plugin_dirs() -> list[Path]:
    """Collect possible Qt plugin directories shipped with PySide6."""

    candidates: list[Path] = []

    qt_plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    if qt_plugins.exists():
        candidates.append(qt_plugins)

    package_plugins = Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
    if package_plugins.exists():
        candidates.append(package_plugins)

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)
    return unique_candidates


def _ensure_qt_plugin_path() -> None:
    """Ensure the Qt platform plugins directory is discoverable.

    Some macOS environments fail to locate the ``cocoa`` platform plugin on
    subsequent launches when the library path cache is lost. We add the
    runtime plugin directories exposed by Qt and the PySide6 package to both
    Qt's internal library search paths and the conventional environment
    variables so that the platform plugin remains available even after
    restarting the application.
    """

    plugin_dirs = _candidate_plugin_dirs()
    if not plugin_dirs:
        return

    existing_paths = {Path(p) for p in QCoreApplication.libraryPaths()}
    for plugin_dir in plugin_dirs:
        if plugin_dir not in existing_paths:
            QCoreApplication.addLibraryPath(str(plugin_dir))

    for env_var in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_PLUGIN_PATH"):
        current = os.environ.get(env_var)
        pieces = current.split(os.pathsep) if current else []
        updated = _dedupe_paths([str(path) for path in plugin_dirs] + pieces)
        os.environ[env_var] = os.pathsep.join(updated)


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
