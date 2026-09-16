import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from joga_app.catalog import CatalogItem
from joga_app.config import Config
from joga_app.core.storage import read_json
import joga_app.swap_backend as swap_backend


class SwapIntegrationTests(unittest.TestCase):
    def test_apply_and_restore_use_transactional_storage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cooked = root / "CookedPCConsole"
            cooked.mkdir()
            source = cooked / "WHEEL_Source_SF.upk"
            target = cooked / "WHEEL_Target_SF.upk"
            source.write_bytes(b"source-data")
            target.write_bytes(b"target-original")

            swap_backend.BACKUPS_DIR = str(root / "userdata" / "backups")
            swap_backend.PRESETS_FILE = str(root / "userdata" / "data" / "presets.json")
            swap_backend.SWAPS_LOG_FILE = str(root / "userdata" / "data" / "history.json")
            swap_backend.GAME_SIG_FILE = str(root / "userdata" / "data" / "game_sig.json")
            swap_backend.TRANSACTIONS_DIR = str(root / "userdata" / "transactions")

            install = {
                "name": "Test",
                "source": "Steam",
                "cookedDir": str(cooked),
            }
            config = Config(installs=[install])
            config._normalise_installs()
            backend = swap_backend.SwapBackend(config)
            source_item = CatalogItem(source.name, "Source", "Wheels")
            target_item = CatalogItem(target.name, "Target", "Wheels")

            result = backend.apply_swap(install, source_item, target_item)
            self.assertTrue(result[0], result)
            self.assertEqual(target.read_bytes(), b"source-data")
            self.assertEqual(len(read_json(swap_backend.SWAPS_LOG_FILE)), 1)
            active = backend.presets.active_swaps()
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0].install_id, install["id"])

            restored = backend.restore_swap(install, active[0])
            self.assertTrue(restored[0], restored)
            self.assertEqual(target.read_bytes(), b"target-original")
            self.assertEqual(backend.presets.active_swaps(), [])

    def test_metadata_failure_rolls_back_game_and_preset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cooked = root / "CookedPCConsole"
            cooked.mkdir()
            source = cooked / "WHEEL_Source_SF.upk"
            target = cooked / "WHEEL_Target_SF.upk"
            source.write_bytes(b"source-data")
            target.write_bytes(b"target-original")

            swap_backend.BACKUPS_DIR = str(root / "userdata" / "backups")
            swap_backend.PRESETS_FILE = str(root / "userdata" / "data" / "presets.json")
            swap_backend.SWAPS_LOG_FILE = str(root / "userdata" / "data" / "history.json")
            swap_backend.GAME_SIG_FILE = str(root / "userdata" / "data" / "game_sig.json")
            swap_backend.TRANSACTIONS_DIR = str(root / "userdata" / "transactions")
            install = {
                "name": "Test",
                "source": "Steam",
                "cookedDir": str(cooked),
            }
            config = Config(installs=[install])
            config._normalise_installs()
            backend = swap_backend.SwapBackend(config)

            with patch.object(backend, "_append_log", side_effect=OSError("disk full")):
                result = backend.apply_swap(
                    install,
                    CatalogItem(source.name, "Source", "Wheels"),
                    CatalogItem(target.name, "Target", "Wheels"),
                )

            self.assertFalse(result[0])
            self.assertEqual(target.read_bytes(), b"target-original")
            self.assertEqual(backend.presets.active_swaps(), [])


if __name__ == "__main__":
    unittest.main()
