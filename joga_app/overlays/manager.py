"""Lifecycle and data coordinator for all external overlay windows."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from joga_app.overlays.config import OVERLAY_DEFINITIONS, OverlayStore
from joga_app.overlays.hotkey import GlobalHotkey
from joga_app.overlays.providers import (
    controller_snapshot,
    keyboard_mouse_snapshot,
    rocket_league_running,
)
from joga_app.overlays.widgets import OverlayWindow


class OverlayManager(QObject):
    state_changed = Signal()
    game_running_changed = Signal(bool)

    def __init__(
        self,
        store: OverlayStore | None = None,
        parent=None,
        *,
        start_timers=True,
        enable_hotkey=True,
    ):
        super().__init__(parent)
        self.store = store or OverlayStore()
        self.windows = {
            overlay_id: OverlayWindow(overlay_id, label)
            for overlay_id, label in OVERLAY_DEFINITIONS
        }
        self.game_running = False
        self._session_started = None
        self._install = None
        self._notification = "No notifications"
        self._notification_until = 0.0
        for window in self.windows.values():
            window.moved.connect(self._save_position)

        self.hotkey = GlobalHotkey(self)
        self.hotkey.activated.connect(self.toggle_global)
        if enable_hotkey:
            self.hotkey.register()

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self._update_values)
        self.process_timer = QTimer(self)
        self.process_timer.setInterval(2000)
        self.process_timer.timeout.connect(self._poll_game)
        if start_timers:
            self.update_timer.start()
            self.process_timer.start()
            QTimer.singleShot(0, self._poll_game)
        self.apply_state()

    def set_install(self, install):
        self._install = install
        self._update_values()

    def set_enabled(self, overlay_id: str, enabled: bool):
        self.store.overlay(overlay_id)["enabled"] = bool(enabled)
        self.store.save()
        self.apply_state()

    def set_scale(self, overlay_id: str, scale: int):
        self.store.overlay(overlay_id)["scale"] = max(50, min(200, int(scale)))
        self.store.save()
        self.apply_state()

    def set_opacity(self, overlay_id: str, opacity: int):
        self.store.overlay(overlay_id)["opacity"] = max(20, min(100, int(opacity)))
        self.store.save()
        self.apply_state()

    def set_click_through(self, overlay_id: str, enabled: bool):
        self.store.overlay(overlay_id)["clickThrough"] = bool(enabled)
        self.store.save()
        self.apply_state()

    def set_auto_show(self, enabled: bool):
        self.store.data["autoShowWithGame"] = bool(enabled)
        self.store.save()
        self.apply_state()

    def set_edit_mode(self, enabled: bool):
        self.store.data["editMode"] = bool(enabled)
        if enabled:
            self.store.data["globalVisible"] = True
        self.store.save()
        self.apply_state()

    def toggle_global(self):
        self.store.data["globalVisible"] = not self.store.data["globalVisible"]
        self.store.save()
        self.apply_state()

    def reset_positions(self):
        self.store.reset_positions()
        self.apply_state()

    def notify(self, message: str, duration_ms: int = 5000):
        self._notification = str(message)[:300]
        self._notification_until = time.monotonic() + max(500, duration_ms) / 1000
        self._update_values()

    def apply_state(self):
        edit_mode = self.store.data["editMode"]
        globally_visible = self.store.data["globalVisible"]
        auto = self.store.data["autoShowWithGame"]
        for overlay_id, window in self.windows.items():
            settings = self.store.overlay(overlay_id)
            window.configure(settings, edit_mode)
            should_show = (
                settings["enabled"]
                and globally_visible
                and (edit_mode or not auto or self.game_running)
            )
            window.setVisible(should_show)
        self._update_values()
        self.state_changed.emit()

    def _save_position(self, overlay_id: str, x: int, y: int):
        settings = self.store.overlay(overlay_id)
        settings["x"] = int(x)
        settings["y"] = int(y)
        self.store.save()
        self.state_changed.emit()

    def _poll_game(self):
        running = rocket_league_running()
        if running == self.game_running:
            return
        self.game_running = running
        self._session_started = time.monotonic() if running else None
        self.game_running_changed.emit(running)
        self.apply_state()

    @staticmethod
    def _duration(seconds: float) -> str:
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _update_values(self):
        self.windows["fps"].set_value("FPS  N/A\nFrame time unavailable")
        self.windows["controller"].set_value(controller_snapshot())
        self.windows["kbm"].set_value(keyboard_mouse_snapshot())
        if self.game_running and self._session_started is not None:
            value = f"ROCKET LEAGUE  ONLINE\n{self._duration(time.monotonic() - self._session_started)}"
        else:
            value = "ROCKET LEAGUE  OFFLINE\n00:00:00"
        self.windows["session"].set_value(value)
        if self._install:
            source = self._install.get("source", "Local")
            name = self._install.get("name", "Installation")
            player = f"LOCAL PLAYER\n{source} · {name}"
        else:
            player = "LOCAL PLAYER\nNo installation selected"
        self.windows["player"].set_value(player)
        if self._notification_until and time.monotonic() > self._notification_until:
            self._notification = "No notifications"
            self._notification_until = 0.0
        self.windows["notifications"].set_value(self._notification)

    def shutdown(self):
        self.update_timer.stop()
        self.process_timer.stop()
        self.hotkey.unregister()
        for window in self.windows.values():
            window.hide()
            window.deleteLater()
