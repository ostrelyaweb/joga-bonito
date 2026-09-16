"""Preview, apply and restore validated Joga Bonito patches."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from joga_app.core.paths import PATHS
from joga_app.core.storage import atomic_write_json, read_json
from joga_app.core.transactions import FileTransaction, ensure_within, file_signature, utc_now
from joga_app.patches.manifest import PatchManifest
from joga_app.patches.packages import PackageImporter


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class PatchPreview:
    compatible: bool
    message: str
    target: Path
    changes: tuple[str, ...] = ()


class PatchService:
    def __init__(
        self,
        *,
        state_path: str | Path | None = None,
        backup_root: str | Path | None = None,
        journal_dir: str | Path | None = None,
        package_root: str | Path | None = None,
    ):
        self.state_path = Path(state_path or (PATHS.data / "patches.json"))
        self.backup_root = Path(backup_root or (PATHS.backups / "patches"))
        self.journal_dir = Path(journal_dir or PATHS.transactions)
        self.importer = PackageImporter(package_root)

    def _state(self) -> dict:
        state = read_json(self.state_path, {}) or {}
        active = state.get("active")
        return {"version": 1, "active": active if isinstance(active, list) else []}

    def active_records(self, install_id: str | None = None) -> list[dict]:
        records = self._state()["active"]
        if install_id is None:
            return records
        return [item for item in records if item.get("installId") == install_id]

    @staticmethod
    def _target(cooked_dir: str | Path, manifest: PatchManifest) -> Path:
        root = Path(cooked_dir).resolve()
        target = (root / manifest.target_file).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("Patch target escapes the game directory") from exc
        return target

    def preview(self, manifest: PatchManifest, cooked_dir: str | Path) -> PatchPreview:
        target = self._target(cooked_dir, manifest)
        if not target.is_file():
            return PatchPreview(False, f"Target file is missing: {target.name}", target)
        if target.stat().st_size != manifest.target_size:
            return PatchPreview(False, "Target size does not match this game build", target)
        if _sha256(target) != manifest.target_sha256:
            return PatchPreview(False, "Target SHA-256 does not match this game build", target)
        changes = []
        with target.open("rb") as handle:
            for operation in manifest.operations:
                handle.seek(operation.offset)
                current = handle.read(len(operation.expected))
                if current != operation.expected:
                    return PatchPreview(
                        False,
                        f"Expected bytes do not match at offset 0x{operation.offset:X}",
                        target,
                    )
                label = operation.label or f"{len(operation.expected)} bytes"
                changes.append(f"0x{operation.offset:X}: {label}")
        return PatchPreview(True, f"Compatible: {len(changes)} verified change(s)", target, tuple(changes))

    def apply(self, manifest: PatchManifest, install: dict) -> tuple[bool, str]:
        install_id = str(install.get("id", "")).strip()
        cooked_dir = install.get("cookedDir", "")
        if not install_id or not cooked_dir:
            return False, "Installation id or CookedPCConsole path is missing"
        if any(
            item.get("installId") == install_id and item.get("patchId") == manifest.patch_id
            for item in self.active_records()
        ):
            return False, "This patch is already active for the selected installation"
        preview = self.preview(manifest, cooked_dir)
        if not preview.compatible:
            return False, preview.message

        target = preview.target
        try:
            backup = ensure_within(
                self.backup_root,
                self.backup_root / install_id / manifest.patch_id / manifest.target_file,
            )
        except ValueError as exc:
            return False, f"Unsafe installation or backup path: {exc}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            if file_signature(backup) != file_signature(target):
                return False, "Existing baseline backup does not match the target file"
        else:
            shutil.copy2(target, backup)

        transaction = FileTransaction(
            "apply_patch",
            Path(cooked_dir),
            install_id=install_id,
            metadata={"patchId": manifest.patch_id},
            journal_dir=self.journal_dir,
        )
        previous_state = self._state()
        try:
            def writer(output):
                shutil.copy2(target, output)
                with open(output, "r+b") as handle:
                    for operation in manifest.operations:
                        handle.seek(operation.offset)
                        if handle.read(len(operation.expected)) != operation.expected:
                            raise ValueError(
                                f"Target changed during apply at 0x{operation.offset:X}"
                            )
                        handle.seek(operation.offset)
                        handle.write(operation.replacement)
                if manifest.output_sha256 and _sha256(Path(output)) != manifest.output_sha256:
                    raise ValueError("Patched output SHA-256 does not match the manifest")

            transaction.replace(target, writer)
            state = self._state()
            state["active"].append(
                {
                    "patchId": manifest.patch_id,
                    "name": manifest.name,
                    "kind": manifest.kind,
                    "installId": install_id,
                    "installName": install.get("name", ""),
                    "targetFile": manifest.target_file,
                    "backup": str(backup),
                    "originalSignature": file_signature(backup),
                    "patchedSignature": file_signature(target),
                    "appliedAt": utc_now(),
                }
            )
            atomic_write_json(self.state_path, state)
            transaction.commit()
            return True, f"Patch applied: {manifest.name}"
        except Exception as exc:
            transaction.rollback()
            atomic_write_json(self.state_path, previous_state)
            return False, f"Patch apply failed and was rolled back: {exc}"

    def restore(self, install: dict, patch_id: str) -> tuple[bool, str]:
        install_id = str(install.get("id", "")).strip()
        records = self._state()["active"]
        record = next(
            (
                item
                for item in records
                if item.get("installId") == install_id and item.get("patchId") == patch_id
            ),
            None,
        )
        if record is None:
            return False, "Active patch record was not found"
        root = Path(install.get("cookedDir", "")).resolve()
        target_file = record.get("targetFile", "")
        if not isinstance(target_file, str) or Path(target_file).name != target_file:
            return False, "Active patch record contains an unsafe target path"
        try:
            target = ensure_within(root, root / target_file)
            backup = ensure_within(
                self.backup_root,
                self.backup_root / install_id / patch_id / target_file,
            )
        except ValueError as exc:
            return False, f"Active patch record contains an unsafe path: {exc}"
        if str(backup) != str(Path(record.get("backup", "")).resolve()):
            return False, "Active patch backup path failed verification"
        if not target.is_file() or not backup.is_file():
            return False, "Target or baseline backup is missing"
        if file_signature(backup) != record.get("originalSignature"):
            return False, "Baseline backup failed integrity verification"
        if file_signature(target) != record.get("patchedSignature"):
            return False, "Target changed after the patch was applied; restore was refused"

        transaction = FileTransaction(
            "restore_patch",
            root,
            install_id=install_id,
            metadata={"patchId": patch_id},
            journal_dir=self.journal_dir,
        )
        previous_state = self._state()
        try:
            transaction.replace(target, lambda output: shutil.copy2(backup, output))
            state = self._state()
            state["active"] = [
                item
                for item in state["active"]
                if not (
                    item.get("installId") == install_id and item.get("patchId") == patch_id
                )
            ]
            atomic_write_json(self.state_path, state)
            transaction.commit()
            return True, f"Original restored: {record.get('name', patch_id)}"
        except Exception as exc:
            transaction.rollback()
            atomic_write_json(self.state_path, previous_state)
            return False, f"Restore failed and was rolled back: {exc}"
