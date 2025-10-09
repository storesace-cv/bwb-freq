"""PySide6 application entry-point for the requisitions UI."""
from __future__ import annotations

import sys
from typing import Sequence

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def run(argv: Sequence[str] | None = None) -> int:
    """Start the Qt application.

    Parameters
    ----------
    argv:
        Optional sequence of command line arguments. Only used to initialise the
        QApplication instance. Defaults to ``sys.argv`` when ``None``.
    """

    app = QApplication(list(argv) if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    raise SystemExit(main())
