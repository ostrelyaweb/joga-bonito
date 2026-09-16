import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from joga_app.core.storage import atomic_write_json, read_json
from joga_app.overlays.config import DEFAULT_POSITIONS, OverlayStore
from joga_app.overlays.manager import OverlayManager


class OverlayConfigTests(unittest.TestCase):
    def test_invalid_values_are_bounded_and_unknown_overlays_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "overlays.json"
            atomic_write_json(
                path,
                {
                    "globalVisible": False,
                    "hotkey": "UNSAFE-CUSTOM-VALUE",
                    "overlays": {
                        "fps": {"scale": 900, "opacity": -20, "x": 999999},
                        "unknown": {"enabled": True},
                    },
                },
            )
            store = OverlayStore(path)
            self.assertFalse(store.data["globalVisible"])
            self.assertEqual(store.data["hotkey"], "F2")
            self.assertEqual(store.overlay("fps")["scale"], 200)
            self.assertEqual(store.overlay("fps")["opacity"], 20)
            self.assertEqual(store.overlay("fps")["x"], 10000)
            self.assertNotIn("unknown", store.data["overlays"])


class OverlayManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_independent_toggle_global_toggle_and_position_persist(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "overlays.json"
            manager = OverlayManager(
                OverlayStore(path), start_timers=False, enable_hotkey=False
            )
            self.addCleanup(manager.shutdown)
            self.assertFalse(any(window.isVisible() for window in manager.windows.values()))

            manager.set_enabled("fps", True)
            self.app.processEvents()
            self.assertTrue(manager.windows["fps"].isVisible())
            self.assertFalse(manager.windows["controller"].isVisible())

            manager.windows["fps"].moved.emit("fps", 321, 654)
            saved = read_json(path)
            self.assertEqual(saved["overlays"]["fps"]["x"], 321)
            self.assertEqual(saved["overlays"]["fps"]["y"], 654)

            manager.toggle_global()
            self.app.processEvents()
            self.assertFalse(manager.windows["fps"].isVisible())
            manager.toggle_global()
            self.app.processEvents()
            self.assertTrue(manager.windows["fps"].isVisible())

    def test_auto_show_and_edit_mode_visibility(self):
        with tempfile.TemporaryDirectory() as temporary:
            manager = OverlayManager(
                OverlayStore(Path(temporary) / "overlays.json"),
                start_timers=False,
                enable_hotkey=False,
            )
            self.addCleanup(manager.shutdown)
            manager.set_enabled("session", True)
            manager.set_auto_show(True)
            self.app.processEvents()
            self.assertFalse(manager.windows["session"].isVisible())

            manager.game_running = True
            manager.apply_state()
            self.app.processEvents()
            self.assertTrue(manager.windows["session"].isVisible())

            manager.game_running = False
            manager.set_edit_mode(True)
            self.app.processEvents()
            self.assertTrue(manager.windows["session"].isVisible())

            manager.reset_positions()
            self.assertEqual(
                (manager.store.overlay("session")["x"], manager.store.overlay("session")["y"]),
                DEFAULT_POSITIONS["session"],
            )


if __name__ == "__main__":
    unittest.main()
