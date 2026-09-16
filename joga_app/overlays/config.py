"""Persistent overlay configuration with bounded values."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from joga_app.core.paths import PATHS
from joga_app.core.storage import atomic_write_json, read_json


OVERLAY_DEFINITIONS = (
    ("fps", "FPS / frame time"),
    ("controller", "Controller input"),
    ("kbm", "Keyboard / mouse"),
    ("session", "Session tracker"),
    ("player", "Platform / player"),
    ("notifications", "Notifications"),
)

DEFAULT_POSITIONS = {
    "fps": (32, 64),
    "controller": (32, 190),
    "kbm": (32, 330),
    "session": (1550, 64),
    "player": (1550, 190),
    "notifications": (650, 64),
}


def default_config() -> dict:
    return {
        "version": 1,
        "globalVisible": True,
        "autoShowWithGame": False,
        "hotkey": "F2",
        "editMode": False,
        "overlays": {
            overlay_id: {
                "enabled": False,
                "x": DEFAULT_POSITIONS[overlay_id][0],
                "y": DEFAULT_POSITIONS[overlay_id][1],
                "scale": 100,
                "opacity": 90,
                "clickThrough": True,
            }
            for overlay_id, _label in OVERLAY_DEFINITIONS
        },
    }


def _bounded_int(value, default, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(minimum, min(maximum, int(value)))


class OverlayStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or (PATHS.config / "overlays.json"))
        self.data = self._normalise(read_json(self.path, {}) or {})

    @staticmethod
    def _normalise(raw: dict) -> dict:
        defaults = default_config()
        if not isinstance(raw, dict):
            return defaults
        result = deepcopy(defaults)
        result["globalVisible"] = bool(raw.get("globalVisible", True))
        result["autoShowWithGame"] = bool(raw.get("autoShowWithGame", False))
        result["editMode"] = bool(raw.get("editMode", False))
        result["hotkey"] = "F2"
        raw_overlays = raw.get("overlays", {})
        if not isinstance(raw_overlays, dict):
            raw_overlays = {}
        for overlay_id, settings in result["overlays"].items():
            incoming = raw_overlays.get(overlay_id, {})
            if not isinstance(incoming, dict):
                continue
            settings["enabled"] = bool(incoming.get("enabled", settings["enabled"]))
            settings["x"] = _bounded_int(incoming.get("x"), settings["x"], -10000, 10000)
            settings["y"] = _bounded_int(incoming.get("y"), settings["y"], -10000, 10000)
            settings["scale"] = _bounded_int(incoming.get("scale"), 100, 50, 200)
            settings["opacity"] = _bounded_int(incoming.get("opacity"), 90, 20, 100)
            settings["clickThrough"] = bool(
                incoming.get("clickThrough", settings["clickThrough"])
            )
        return result

    def overlay(self, overlay_id: str) -> dict:
        return self.data["overlays"][overlay_id]

    def save(self) -> None:
        atomic_write_json(self.path, self.data)

    def reset_positions(self) -> None:
        for overlay_id, position in DEFAULT_POSITIONS.items():
            self.data["overlays"][overlay_id]["x"] = position[0]
            self.data["overlays"][overlay_id]["y"] = position[1]
        self.save()
