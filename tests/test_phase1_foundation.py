import json
import os
import tempfile
import unittest
from pathlib import Path

from joga_app.core.migrations import migrate_legacy_data
from joga_app.core.paths import PathLayout
from joga_app.core.storage import atomic_write_json, read_json
from joga_app.core.transactions import FileTransaction, ensure_within


class AtomicStorageTests(unittest.TestCase):
    def test_atomic_json_round_trip_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nested" / "state.json"
            atomic_write_json(path, {"name": "Joga", "enabled": True})
            self.assertEqual(read_json(path), {"name": "Joga", "enabled": True})
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


class MigrationTests(unittest.TestCase):
    def test_migration_copies_legacy_state_once_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = root / "program"
            program.mkdir()
            (program / "settings.json").write_text(
                json.dumps({"theme": "dark"}), encoding="utf-8"
            )
            legacy_backup = program / "Backups" / "Steam"
            legacy_backup.mkdir(parents=True)
            (legacy_backup / "target.upk").write_bytes(b"original")
            layout = PathLayout(root / "userdata")

            result = migrate_legacy_data(program, layout)
            self.assertIn("settings.json", result["copied"])
            self.assertEqual(
                read_json(layout.config / "settings.json"), {"theme": "dark"}
            )
            self.assertEqual(
                (layout.backups / "Steam" / "target.upk").read_bytes(), b"original"
            )

            atomic_write_json(layout.config / "settings.json", {"theme": "light"})
            migrate_legacy_data(program, layout)
            self.assertEqual(
                read_json(layout.config / "settings.json"), {"theme": "light"}
            )


class TransactionTests(unittest.TestCase):
    def test_commit_replaces_file_and_removes_rollback_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "game"
            journals = Path(temporary) / "journals"
            root.mkdir()
            target = root / "target.upk"
            target.write_bytes(b"before")
            transaction = FileTransaction("test", root, journal_dir=journals)
            transaction.replace(target, lambda output: Path(output).write_bytes(b"after"))
            transaction.commit()
            self.assertEqual(target.read_bytes(), b"after")
            self.assertEqual(read_json(transaction.journal_path)["status"], "committed")
            self.assertFalse(transaction.rollback_dir.exists())

    def test_rollback_restores_every_applied_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "game"
            journals = Path(temporary) / "journals"
            root.mkdir()
            first = root / "first.upk"
            second = root / "second.upk"
            first.write_bytes(b"first-original")
            second.write_bytes(b"second-original")
            transaction = FileTransaction("test", root, journal_dir=journals)
            transaction.replace(first, lambda output: Path(output).write_bytes(b"changed"))

            def fail(_output):
                raise RuntimeError("injected failure")

            with self.assertRaises(RuntimeError):
                transaction.replace(second, fail)
            self.assertEqual(transaction.rollback(), [])
            self.assertEqual(first.read_bytes(), b"first-original")
            self.assertEqual(second.read_bytes(), b"second-original")

    def test_startup_recovery_rolls_back_unfinished_transaction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "game"
            journals = Path(temporary) / "journals"
            root.mkdir()
            target = root / "target.upk"
            target.write_bytes(b"original")
            transaction = FileTransaction("test", root, journal_dir=journals)
            transaction.replace(target, lambda output: Path(output).write_bytes(b"changed"))
            recovered = FileTransaction.recover_incomplete(journals)
            self.assertIn(transaction.id, recovered)
            self.assertEqual(target.read_bytes(), b"original")

    def test_managed_root_rejects_directory_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "game"
            root.mkdir()
            with self.assertRaises(ValueError):
                ensure_within(root, root / ".." / "outside.upk")

    def test_recovery_rejects_tampered_target_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "game"
            journals = base / "journals"
            root.mkdir()
            target = root / "target.upk"
            outside = base / "outside.upk"
            target.write_bytes(b"original")
            outside.write_bytes(b"outside-original")
            transaction = FileTransaction("test", root, journal_dir=journals)
            transaction.replace(target, lambda output: Path(output).write_bytes(b"changed"))
            journal = read_json(transaction.journal_path)
            journal["actions"][0]["target"] = str(outside)
            atomic_write_json(transaction.journal_path, journal)

            self.assertEqual(FileTransaction.recover_incomplete(journals), [])
            self.assertEqual(outside.read_bytes(), b"outside-original")
            self.assertEqual(
                read_json(transaction.journal_path)["status"], "rollback_failed"
            )


if __name__ == "__main__":
    unittest.main()
