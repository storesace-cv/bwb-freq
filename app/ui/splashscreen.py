"""Splash screen implemented with wxPython."""
from __future__ import annotations

from typing import Callable

import wx

from app.ui.assets import BACKGROUND_IMAGE, SPLASH_IMAGE
from app.ui.background_utils import BackgroundLayer, ensure_transparent


class SplashScreen(wx.Frame):
    """Simple splash screen that closes when the user clicks it."""

    def __init__(self, *, on_click: Callable[[], None], auto_dismiss_ms: int | None = 2500) -> None:
        style = wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.BORDER_NONE
        super().__init__(None, title="Bem-vindo", style=style)

        self._callback = on_click
        self._is_available = False
        self._dismissed = False
        self._auto_timer: wx.CallLater | None = None

        panel = wx.Panel(self)
        ensure_transparent(panel)

        self._background = BackgroundLayer(panel, BACKGROUND_IMAGE, "splash-background")
        self._image: wx.StaticBitmap | None = None

        splash_bitmap = None
        if SPLASH_IMAGE.exists():
            try:
                splash_bitmap = wx.Bitmap(str(SPLASH_IMAGE))
            except Exception:  # pragma: no cover - invalid/corrupt file
                splash_bitmap = None

        layout = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(layout)

        if splash_bitmap and splash_bitmap.IsOk():
            image = wx.StaticBitmap(panel, bitmap=splash_bitmap)
            image.SetName("splash-image")
            self._image = image
            layout.AddStretchSpacer()
            layout.Add(image, 0, wx.ALIGN_CENTER | wx.ALL, 0)
            layout.AddStretchSpacer()
            width, height = splash_bitmap.GetSize()
            self.SetClientSize((width, height))
            self._is_available = True
        elif self._background.label is not None:
            width, height = self._background.label.GetSize()
            self.SetClientSize((width, height))
            self._is_available = True
        else:
            # Fallback size when no image could be loaded.
            self.SetClientSize((800, 500))

        panel.Layout()
        self._bind_events(panel)

        if auto_dismiss_ms is not None and auto_dismiss_ms > 0:
            self._auto_timer = wx.CallLater(auto_dismiss_ms, self._handle_timeout)

    @property
    def is_available(self) -> bool:
        return self._is_available

    def _bind_events(self, panel: wx.Panel) -> None:
        self.Bind(wx.EVT_LEFT_UP, self._handle_click)
        self.Bind(wx.EVT_RIGHT_UP, self._handle_click)

        panel.Bind(wx.EVT_LEFT_UP, self._handle_click)
        panel.Bind(wx.EVT_RIGHT_UP, self._handle_click)
        panel.Bind(wx.EVT_CHAR_HOOK, self._handle_key)

        if self._image is not None:
            self._image.Bind(wx.EVT_LEFT_UP, self._handle_click)
            self._image.Bind(wx.EVT_RIGHT_UP, self._handle_click)

        if self._background.label is not None:
            self._background.label.Bind(wx.EVT_LEFT_UP, self._handle_click)
            self._background.label.Bind(wx.EVT_RIGHT_UP, self._handle_click)

    def _handle_click(self, _event: wx.Event) -> None:
        self._invoke_callback()

    def _handle_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in {wx.WXK_ESCAPE, wx.WXK_RETURN, wx.WXK_SPACE}:
            self._invoke_callback()
        else:
            event.Skip()

    def _handle_timeout(self) -> None:
        self._invoke_callback()

    def _invoke_callback(self) -> None:
        if self._dismissed:
            return

        self._dismissed = True
        if self._auto_timer is not None:
            self._auto_timer.Stop()
            self._auto_timer = None
        self.Hide()

        def _finalise() -> None:
            try:
                self._callback()
            finally:
                if not self.IsBeingDeleted():
                    self.Destroy()

        wx.CallAfter(_finalise)
