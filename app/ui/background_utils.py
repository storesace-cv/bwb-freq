"""Helper utilities for dealing with background images in wxPython widgets."""
from __future__ import annotations

from pathlib import Path

import wx


def ensure_transparent(window: wx.Window) -> None:
    """Best-effort attempt to make *window* paint with a transparent background."""

    window.SetBackgroundStyle(wx.BG_STYLE_PAINT)


class BackgroundLayer:
    """Keep a background bitmap scaled to the hosting window size."""

    def __init__(self, host: wx.Window, image_path: Path, name: str = "background") -> None:
        self.host = host
        self.image_path = image_path
        self.name = name
        self._original_bitmap: wx.Bitmap | None = None
        self._label: wx.StaticBitmap | None = None

        if not image_path.exists():
            return

        try:
            bitmap = wx.Bitmap(str(image_path))
        except Exception:  # pragma: no cover - invalid/corrupt image
            return

        if not bitmap.IsOk():
            return

        self._original_bitmap = bitmap
        self._label = wx.StaticBitmap(host, bitmap=bitmap)
        self._label.SetName(self.name)
        self._label.Disable()
        self._label.Move((0, 0))
        self._label.Lower()

        self.host.Bind(wx.EVT_SIZE, self._on_host_size)
        self.host.Bind(wx.EVT_WINDOW_DESTROY, self._on_host_destroy)
        self._sync_to_host()

    @property
    def label(self) -> wx.StaticBitmap | None:
        """Expose the underlying ``wx.StaticBitmap`` for customisation."""

        return self._label

    def _on_host_size(self, event: wx.Event) -> None:
        self._sync_to_host()
        event.Skip()

    def _on_host_destroy(self, _event: wx.Event) -> None:
        if self._label is not None:
            self._label.Destroy()
            self._label = None

    def _sync_to_host(self) -> None:
        if self._label is None or self._original_bitmap is None:
            return

        size = self.host.GetClientSize()
        if size.width <= 0 or size.height <= 0:
            return

        image = self._original_bitmap.ConvertToImage()
        scaled = image.Scale(size.width, size.height, wx.IMAGE_QUALITY_HIGH)
        self._label.SetBitmap(wx.Bitmap(scaled))
        self._label.SetSize(size)
        self._label.Move((0, 0))


__all__ = ["BackgroundLayer", "ensure_transparent"]
