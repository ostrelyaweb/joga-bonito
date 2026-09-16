from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from joga_app.core.paths import PATHS
from joga_app.core.storage import atomic_write_json, read_json
from joga_app.core.transactions import FileTransaction, ensure_within, file_signature, utc_now
from joga_app.overlays.providers import rocket_league_running
from joga_app.workshop.packages import WorkshopImporter


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class WorkshopPreview:
    compatible: bool
    message: str
    actions: tuple[str, ...] = ()


class WorkshopService:
    def __init__(self, *, state_path=None, backup_root=None, journal_dir=None, library_root=None, game_running_check=None):
        self.state_path = Path(state_path or (PATHS.data / "workshop.json"))
        self.backup_root = Path(backup_root or (PATHS.backups / "workshop"))
        self.journal_dir = Path(journal_dir or PATHS.transactions)
        self.importer = WorkshopImporter(library_root)
        self.game_running_check = game_running_check or rocket_league_running

    def _state(self):
        data = read_json(self.state_path, {}) or {}
        return {"version": 1, "installed": data.get("installed", []) if isinstance(data.get("installed", []), list) else []}

    def installed(self, install_id=None):
        records = self._state()["installed"]
        return records if install_id is None else [r for r in records if r.get("installId") == install_id]

    def preview(self, manifest, folder, install):
        root = Path(install.get("cookedDir", "")).resolve()
        if not root.is_dir():
            return WorkshopPreview(False, "CookedPCConsole directory is missing")
        actions = []
        for entry in manifest.files:
            source = ensure_within(folder, Path(folder) / Path(entry.source))
            target = ensure_within(root, root / entry.target)
            if not source.is_file() or source.stat().st_size != entry.size or sha256(source) != entry.sha256:
                return WorkshopPreview(False, f"Imported payload failed verification: {entry.source}")
            if entry.mode == "add":
                if target.exists():
                    return WorkshopPreview(False, f"Add target already exists: {entry.target}")
            else:
                if not target.is_file() or target.stat().st_size != entry.target_size or sha256(target) != entry.target_sha256:
                    return WorkshopPreview(False, f"Replace target does not match this game build: {entry.target}")
            actions.append(f"{entry.mode.upper()}  {entry.target}  ({entry.size} bytes)")
        return WorkshopPreview(True, f"Compatible: {len(actions)} verified file action(s)", tuple(actions))

    def install(self, manifest, folder, install):
        install_id = str(install.get("id", ""))
        if not install_id:
            return False, "Installation id is missing"
        if self.game_running_check():
            return False, "Close Rocket League before installing Workshop content"
        if any(r.get("installId") == install_id and r.get("packageId") == manifest.package_id for r in self.installed()):
            return False, "This package is already installed"
        preview = self.preview(manifest, folder, install)
        if not preview.compatible:
            return False, preview.message
        root = Path(install["cookedDir"]).resolve()
        transaction = FileTransaction("workshop_install", root, install_id, {"packageId": manifest.package_id}, self.journal_dir)
        previous = self._state()
        records = []
        try:
            for entry in manifest.files:
                source = ensure_within(folder, Path(folder) / entry.source)
                target = ensure_within(root, root / entry.target)
                backup = ""
                if entry.mode == "replace":
                    backup_path = ensure_within(self.backup_root, self.backup_root / install_id / manifest.package_id / entry.target)
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    if backup_path.exists():
                        if file_signature(backup_path) != file_signature(target):
                            raise ValueError(f"Existing backup does not match: {entry.target}")
                    else:
                        shutil.copy2(target, backup_path)
                    backup = str(backup_path)
                    transaction.replace(target, lambda output, src=source: shutil.copy2(src, output))
                else:
                    transaction.create(target, lambda output, src=source: shutil.copy2(src, output))
                records.append({"target": entry.target, "mode": entry.mode, "backup": backup, "backupSignature": file_signature(backup) if backup else "", "installedSignature": file_signature(target)})
            state = self._state()
            state["installed"].append({"packageId": manifest.package_id, "name": manifest.name, "category": manifest.category, "installId": install_id, "installedAt": utc_now(), "files": records})
            atomic_write_json(self.state_path, state)
            transaction.commit()
            return True, f"Workshop package installed: {manifest.name}"
        except Exception as exc:
            transaction.rollback()
            atomic_write_json(self.state_path, previous)
            return False, f"Install failed and was rolled back: {exc}"

    def restore(self, package_id, install):
        install_id = str(install.get("id", ""))
        record = next((r for r in self.installed() if r.get("installId") == install_id and r.get("packageId") == package_id), None)
        if not record:
            return False, "Installed package record not found"
        if self.game_running_check():
            return False, "Close Rocket League before restoring Workshop content"
        root = Path(install.get("cookedDir", "")).resolve()
        try:
            for item in record["files"]:
                target = ensure_within(root, root / item["target"])
                if not target.is_file() or file_signature(target) != item["installedSignature"]:
                    return False, f"Installed file changed; restore refused: {item['target']}"
                if item["mode"] == "replace":
                    backup = ensure_within(self.backup_root, item["backup"])
                    if not backup.is_file() or file_signature(backup) != item.get("backupSignature"):
                        return False, f"Verified backup is missing or changed: {item['target']}"
        except (KeyError, ValueError) as exc:
            return False, f"Unsafe installed package record: {exc}"
        transaction = FileTransaction("workshop_restore", root, install_id, {"packageId": package_id}, self.journal_dir)
        previous = self._state()
        try:
            for item in reversed(record["files"]):
                target = ensure_within(root, root / item["target"])
                if item["mode"] == "add":
                    transaction.delete(target)
                else:
                    backup = ensure_within(self.backup_root, item["backup"])
                    transaction.replace(target, lambda output, src=backup: shutil.copy2(src, output))
            state = self._state()
            state["installed"] = [r for r in state["installed"] if not (r.get("installId") == install_id and r.get("packageId") == package_id)]
            atomic_write_json(self.state_path, state)
            transaction.commit()
            return True, f"Workshop package restored: {record.get('name', package_id)}"
        except Exception as exc:
            transaction.rollback()
            atomic_write_json(self.state_path, previous)
            return False, f"Restore failed and was rolled back: {exc}"

    def remove_imported(self, manifest, folder):
        if any(record.get("packageId") == manifest.package_id for record in self.installed()):
            return False, "Restore this package from every installation before removing it"
        try:
            managed = ensure_within(self.importer.root, folder)
            if managed.parent.name != manifest.category or managed.name != manifest.package_id:
                raise ValueError("Package library path does not match its manifest")
            shutil.rmtree(managed)
            return True, f"Imported package removed: {manifest.name}"
        except (OSError, ValueError) as exc:
            return False, f"Package removal failed: {exc}"
