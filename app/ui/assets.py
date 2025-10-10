"""Shared UI asset paths used across the tkinter interface."""
from __future__ import annotations

from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent

# Application icon displayed on top-level windows.
APP_ICON = _BASE_DIR / "restaurant_order_icon.png"

# Transparent PNG used behind the splash screen and main window widgets.
BACKGROUND_IMAGE = _BASE_DIR / "bwb-Splash-background.png"

# Foreground image displayed on the splash dialog.
SPLASH_IMAGE = _BASE_DIR / "bwb-Splash.png"


__all__ = ["APP_ICON", "BACKGROUND_IMAGE", "SPLASH_IMAGE"]
