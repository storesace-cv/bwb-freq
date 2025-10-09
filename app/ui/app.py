"""PySide6 application entry-point for the requisitions UI."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Iterable, Sequence

import PySide6
from PySide6.QtCore import QCoreApplication, QLibraryInfo, Qt
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.splashscreen import SplashScreen


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


def _candidate_plugin_roots() -> list[Path]:
    """Return Qt plugin root directories to probe for platform libraries."""

    candidates: list[Path] = []

    qt_plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    if qt_plugins.is_dir():
        candidates.append(qt_plugins)

    package_plugins = Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
    if package_plugins.is_dir():
        candidates.append(package_plugins)

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)
    return unique_candidates


def _candidate_platform_dirs(plugin_roots: Iterable[Path]) -> list[Path]:
    """Return directories that contain Qt *platform* plugins."""

    platforms: list[Path] = []
    seen: set[Path] = set()
    for root in plugin_roots:
        # Typical layout is ``plugins/platforms``. Some environments already
        # expose the ``platforms`` folder directly as a library path.
        direct = root / "platforms"
        if direct.is_dir() and direct not in seen:
            seen.add(direct)
            platforms.append(direct)
        elif root.name == "platforms" and root not in seen:
            seen.add(root)
            platforms.append(root)
    return platforms


def _merge_env_paths(
    env_var: str,
    new_paths: Sequence[Path],
    *,
    allow_multiple: bool = True,
) -> None:
    """Merge ``new_paths`` into ``env_var`` while keeping existing entries."""

    if not new_paths:
        return

    existing_raw = os.environ.get(env_var)
    existing_parts = existing_raw.split(os.pathsep) if existing_raw else []
    merged = _dedupe_paths([str(path) for path in new_paths] + existing_parts)
    if not merged:
        return

    if allow_multiple:
        os.environ[env_var] = os.pathsep.join(merged)
    else:
        # Some Qt environment variables (notably QT_QPA_PLATFORM_PLUGIN_PATH)
        # only support a single directory. Preserve user-provided values if
        # present, otherwise use the first detected location.
        if existing_parts:
            os.environ[env_var] = existing_parts[0]
        else:
            os.environ[env_var] = merged[0]


def _ensure_qt_plugin_path() -> None:
    """Ensure the Qt platform plugins directory is discoverable.

    Some macOS environments fail to locate the ``cocoa`` platform plugin on
    subsequent launches when the library path cache is lost. We add the
    runtime plugin directories exposed by Qt and the PySide6 package to both
    Qt's internal library search paths and the conventional environment
    variables so that the platform plugin remains available even after
    restarting the application.
    """

    plugin_roots = _candidate_plugin_roots()
    if not plugin_roots:
        return

    existing_paths = {Path(p) for p in QCoreApplication.libraryPaths()}
    for plugin_dir in plugin_roots:
        if plugin_dir not in existing_paths:
            QCoreApplication.addLibraryPath(str(plugin_dir))

    platform_dirs = _candidate_platform_dirs(plugin_roots)
    for platform_dir in platform_dirs:
        if platform_dir not in existing_paths:
            QCoreApplication.addLibraryPath(str(platform_dir))

    _merge_env_paths("QT_PLUGIN_PATH", plugin_roots)
    _merge_env_paths(
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        platform_dirs,
        allow_multiple=False,
    )


def run(argv: Sequence[str] | None = None) -> int:
    """Start the Qt application.

    Parameters
    ----------
    argv:
        Optional sequence of command line arguments. Only used to initialise the
        QApplication instance. Defaults to ``sys.argv`` when ``None``.
    """

    _ensure_qt_plugin_path()

    QCoreApplication.setAttribute(
        Qt.ApplicationAttribute.AA_TranslucentBackground,
        True,
    )
    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setStyleSheet(
        "QMainWindow { background: transparent; }\n"
        "QWidget { background: transparent; }"
    )

    splash = SplashScreen()
    splash.show()

    window: MainWindow | None = None

    def _launch_main_window() -> None:
        nonlocal window
        if window is None:
            splash.close()
            window = MainWindow()
            window.show()

    splash.clicked.connect(_launch_main_window)

    return app.exec()


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    raise SystemExit(main())
