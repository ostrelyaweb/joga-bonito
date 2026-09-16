import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from joga_app.patches.builders import build_paint_patch, build_redirect_patch
from joga_app.patches.engine import PatchService
from joga_app.patches.manifest import PatchManifest, PatchValidationError
from joga_app.patches.packages import PackageImportError, PackageImporter
from joga_app.core.storage import atomic_write_json


def manifest_for(path: Path, operations, patch_id="test.patch"):
    payload = path.read_bytes()
    return PatchManifest.from_dict(
        {
            "format": "joga-bonito.patch",
            "version": 1,
            "id": patch_id,
            "name": "Test Patch",
            "author": "Joga Tests",
            "kind": "paint",
            "target": {
                "file": path.name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            "operations": operations,
        }
    )


class ManifestTests(unittest.TestCase):
    def test_accepts_strict_valid_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target.upk"
            target.write_bytes(b"01234567")
            manifest = manifest_for(
                target,
                [{"offset": 2, "expected": "3233", "replacement": "aabb"}],
            )
            self.assertEqual(manifest.target_file, "target.upk")
            self.assertEqual(manifest.operations[0].replacement, bytes.fromhex("aabb"))

    def test_rejects_overlap_and_changed_length(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target.upk"
            target.write_bytes(b"01234567")
            with self.assertRaises(PatchValidationError):
                manifest_for(
                    target,
                    [
                        {"offset": 1, "expected": "3132", "replacement": "aaaa"},
                        {"offset": 2, "expected": "3233", "replacement": "bbbb"},
                    ],
                )
            with self.assertRaises(PatchValidationError):
                manifest_for(
                    target,
                    [{"offset": 1, "expected": "31", "replacement": "aaaa"}],
                )


class EngineTests(unittest.TestCase):
    def test_preview_apply_and_restore_are_transactional(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "CookedPCConsole"
            game.mkdir()
            target = game / "target.upk"
            target.write_bytes(b"HEADER-red-FOOTER")
            manifest = manifest_for(
                target,
                [{"offset": 7, "expected": b"red".hex(), "replacement": b"blu".hex()}],
            )
            service = PatchService(
                state_path=root / "data" / "patches.json",
                backup_root=root / "backups",
                journal_dir=root / "transactions",
                package_root=root / "packages",
            )
            install = {"id": "install-1", "name": "Test", "cookedDir": str(game)}

            preview = service.preview(manifest, game)
            self.assertTrue(preview.compatible)
            self.assertEqual(target.read_bytes(), b"HEADER-red-FOOTER")
            ok, _message = service.apply(manifest, install)
            self.assertTrue(ok)
            self.assertEqual(target.read_bytes(), b"HEADER-blu-FOOTER")
            self.assertEqual(len(service.active_records("install-1")), 1)

            ok, _message = service.restore(install, manifest.patch_id)
            self.assertTrue(ok)
            self.assertEqual(target.read_bytes(), b"HEADER-red-FOOTER")
            self.assertEqual(service.active_records("install-1"), [])

    def test_preview_rejects_wrong_game_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target.upk"
            target.write_bytes(b"original")
            manifest = manifest_for(
                target,
                [{"offset": 0, "expected": b"o".hex(), "replacement": b"O".hex()}],
            )
            target.write_bytes(b"modified")
            service = PatchService(
                state_path=Path(temporary) / "state.json",
                backup_root=Path(temporary) / "backups",
                journal_dir=Path(temporary) / "transactions",
                package_root=Path(temporary) / "packages",
            )
            preview = service.preview(manifest, temporary)
            self.assertFalse(preview.compatible)
            self.assertIn("SHA-256", preview.message)

    def test_restore_rejects_tampered_state_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            game.mkdir()
            outside = root / "outside.upk"
            outside.write_bytes(b"do-not-touch")
            state = root / "patches.json"
            atomic_write_json(
                state,
                {
                    "version": 1,
                    "active": [
                        {
                            "installId": "install-1",
                            "patchId": "test.patch",
                            "targetFile": "../outside.upk",
                            "backup": str(outside),
                            "originalSignature": "tampered",
                        }
                    ],
                },
            )
            service = PatchService(
                state_path=state,
                backup_root=root / "backups",
                journal_dir=root / "transactions",
                package_root=root / "packages",
            )
            ok, message = service.restore(
                {"id": "install-1", "cookedDir": str(game)}, "test.patch"
            )
            self.assertFalse(ok)
            self.assertIn("unsafe", message.lower())
            self.assertEqual(outside.read_bytes(), b"do-not-touch")

    def test_restore_refuses_to_overwrite_a_later_game_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            game.mkdir()
            target = game / "target.upk"
            target.write_bytes(b"original")
            manifest = manifest_for(
                target,
                [{"offset": 0, "expected": "6f", "replacement": "4f"}],
            )
            service = PatchService(
                state_path=root / "state.json",
                backup_root=root / "backups",
                journal_dir=root / "transactions",
                package_root=root / "packages",
            )
            install = {"id": "install-1", "cookedDir": str(game)}
            self.assertTrue(service.apply(manifest, install)[0])
            target.write_bytes(b"game-update")
            ok, message = service.restore(install, manifest.patch_id)
            self.assertFalse(ok)
            self.assertIn("changed", message)
            self.assertEqual(target.read_bytes(), b"game-update")


class BuilderTests(unittest.TestCase):
    def test_redirect_requires_unique_or_explicit_exact_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "redirect.upk"
            target.write_bytes(b"xxOLDyyOLDzz")
            with self.assertRaises(ValueError):
                build_redirect_patch(
                    target,
                    "OLD",
                    "NEW",
                    patch_id="redirect.test",
                    name="Redirect",
                    author="Tests",
                )
            manifest = build_redirect_patch(
                target,
                "OLD",
                "NEW",
                offsets=[2],
                patch_id="redirect.test",
                name="Redirect",
                author="Tests",
            )
            self.assertEqual(manifest.operations[0].offset, 2)
            with self.assertRaises(ValueError):
                build_redirect_patch(
                    target,
                    "OLD",
                    "LONG",
                    patch_id="redirect.bad",
                    name="Bad",
                    author="Tests",
                )

    def test_paint_requires_explicit_matching_offset(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "paint.upk"
            target.write_bytes(b"xx\x10\x20\x30\xffyy")
            manifest = build_paint_patch(
                target,
                2,
                b"\x10\x20\x30\xff",
                b"\x40\x50\x60\xff",
                patch_id="paint.test",
                name="Paint",
                author="Tests",
            )
            self.assertEqual(manifest.operations[0].offset, 2)
            with self.assertRaises(ValueError):
                build_paint_patch(
                    target,
                    3,
                    b"\x10\x20\x30\xff",
                    b"\x40\x50\x60\xff",
                    patch_id="paint.bad",
                    name="Bad",
                    author="Tests",
                )


class PackageTests(unittest.TestCase):
    def test_imports_valid_package_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.upk"
            target.write_bytes(b"abcd")
            manifest = manifest_for(
                target,
                [{"offset": 0, "expected": "61", "replacement": "62"}],
                patch_id="package.test",
            )
            valid = root / "valid.jbpkg"
            with zipfile.ZipFile(valid, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest.to_dict()))
                archive.writestr("preview.png", b"png")
            importer = PackageImporter(root / "library")
            imported, folder = importer.import_package(valid)
            self.assertEqual(imported.patch_id, "package.test")
            self.assertTrue((folder / "manifest.json").is_file())

            malicious = root / "malicious.jbpkg"
            with zipfile.ZipFile(malicious, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest.to_dict()))
                archive.writestr("../escape.json", "{}")
            with self.assertRaises(PackageImportError):
                PackageImporter(root / "other-library").import_package(malicious)
            self.assertFalse((root / "escape.json").exists())


if __name__ == "__main__":
    unittest.main()
