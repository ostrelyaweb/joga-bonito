import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from joga_app.core.transactions import FileTransaction
from joga_app.workshop.manifest import WorkshopManifest, WorkshopValidationError
from joga_app.workshop.packages import WorkshopImportError, WorkshopImporter
from joga_app.workshop.service import WorkshopService


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest_dict(files, package_id="test.pack"):
    return {
        "format": "joga-bonito.workshop",
        "version": 1,
        "id": package_id,
        "name": "Test Workshop Pack",
        "author": "Joga Tests",
        "category": "maps",
        "description": "Synthetic test package",
        "files": files,
    }


class ExtendedTransactionTests(unittest.TestCase):
    def test_create_and_delete_roll_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "game"
            root.mkdir()
            journals = Path(temporary) / "journals"
            created = root / "created.upk"
            existing = root / "existing.upk"
            existing.write_bytes(b"before")
            transaction = FileTransaction("extended", root, journal_dir=journals)
            transaction.create(created, lambda output: Path(output).write_bytes(b"new"))
            transaction.delete(existing)
            self.assertTrue(created.exists())
            self.assertFalse(existing.exists())
            self.assertEqual(transaction.rollback(), [])
            self.assertFalse(created.exists())
            self.assertEqual(existing.read_bytes(), b"before")


class WorkshopManifestTests(unittest.TestCase):
    def test_replace_requires_exact_target_signature(self):
        payload = b"replacement"
        with self.assertRaises(WorkshopValidationError):
            WorkshopManifest.from_dict(
                manifest_dict(
                    [{"source": "payload/map.upk", "target": "map.upk", "mode": "replace", "size": len(payload), "sha256": digest(payload)}]
                )
            )


class WorkshopIntegrationTests(unittest.TestCase):
    def _service(self, root):
        return WorkshopService(
            state_path=root / "state.json",
            backup_root=root / "backups",
            journal_dir=root / "transactions",
            library_root=root / "library",
            game_running_check=lambda: False,
        )

    def test_import_install_and_restore_add_and_replace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            game.mkdir()
            original = b"original-game-file"
            replacement = b"replacement-data"
            added = b"new-workshop-map"
            (game / "existing.upk").write_bytes(original)
            files = [
                {"source": "payload/existing.upk", "target": "existing.upk", "mode": "replace", "size": len(replacement), "sha256": digest(replacement), "targetSize": len(original), "targetSha256": digest(original)},
                {"source": "payload/newmap.upk", "target": "newmap.upk", "mode": "add", "size": len(added), "sha256": digest(added)},
            ]
            archive_path = root / "pack.jbworkshop"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest_dict(files)))
                archive.writestr("payload/existing.upk", replacement)
                archive.writestr("payload/newmap.upk", added)
            service = self._service(root)
            manifest, folder = service.importer.import_package(archive_path)
            install = {"id": "install-1", "cookedDir": str(game)}
            self.assertTrue(service.preview(manifest, folder, install).compatible)
            self.assertTrue(service.install(manifest, folder, install)[0])
            self.assertEqual((game / "existing.upk").read_bytes(), replacement)
            self.assertEqual((game / "newmap.upk").read_bytes(), added)
            self.assertTrue(service.restore(manifest.package_id, install)[0])
            self.assertEqual((game / "existing.upk").read_bytes(), original)
            self.assertFalse((game / "newmap.upk").exists())
            self.assertTrue(service.remove_imported(manifest, folder)[0])
            self.assertFalse(folder.exists())

    def test_import_rejects_traversal_and_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b"map"
            files = [{"source": "payload/map.upk", "target": "map.upk", "mode": "add", "size": len(payload), "sha256": digest(payload)}]
            for name, extra in (("traversal", "../escape.json"), ("executable", "payload/run.exe")):
                archive_path = root / f"{name}.jbworkshop"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr("manifest.json", json.dumps(manifest_dict(files, f"test.{name}")))
                    archive.writestr("payload/map.upk", payload)
                    archive.writestr(extra, b"bad")
                with self.assertRaises(WorkshopImportError):
                    WorkshopImporter(root / f"library-{name}").import_package(archive_path)
            self.assertFalse((root / "escape.json").exists())


if __name__ == "__main__":
    unittest.main()
