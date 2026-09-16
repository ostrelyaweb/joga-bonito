"""Best-effort Windows global hotkey registration for F2."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal
from PySide6.QtWidgets import QApplication


WM_HOTKEY = 0x0312
VK_F2 = 0x71
HOTKEY_ID = 0x4A42


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):
        if os.name == "nt" and event_type in {b"windows_generic_MSG", b"windows_dispatcher_MSG"}:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.owner.activated.emit()
        return False, 0


class GlobalHotkey(QObject):
    activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.registered = False
        self._filter = _Filter(self)

    def register(self) -> bool:
        if os.name != "nt" or QApplication.instance() is None:
            return False
        if self.registered:
            return True
        self.registered = bool(ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, 0, VK_F2))
        if self.registered:
            QApplication.instance().installNativeEventFilter(self._filter)
        return self.registered

    def unregister(self):
        if self.registered and os.name == "nt":
            QApplication.instance().removeNativeEventFilter(self._filter)
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
        self.registered = False
