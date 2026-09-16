import hashlib
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from joga_app.core.paths import PATHS
from joga_app.core.storage import atomic_write_json, read_json


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_signature(path) -> str:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return f"{size}:{digest.hexdigest()}"


def ensure_within(root, candidate) -> Path:
    root_path = Path(root).resolve()
    candidate_path = Path(candidate).resolve()
    try:
        candidate_path.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(f"Path escapes the managed root: {candidate_path}") from exc
    return candidate_path


class FileTransaction:
    """Journaled, recoverable set of atomic file replacements."""

    def __init__(self, kind, managed_root, install_id="", metadata=None, journal_dir=None):
        self.id = uuid.uuid4().hex
        self.kind = kind
        self.managed_root = Path(managed_root).resolve()
        self.install_id = install_id
        self.journal_dir = Path(journal_dir or PATHS.transactions)
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.rollback_dir = self.journal_dir / f"{self.id}.files"
        self.rollback_dir.mkdir(parents=True, exist_ok=False)
        self.journal_path = self.journal_dir / f"{self.id}.json"
        self.data = {
            "version": 1,
            "id": self.id,
            "kind": kind,
            "installId": install_id,
            "managedRoot": str(self.managed_root),
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "status": "active",
            "metadata": metadata or {},
            "actions": [],
        }
        self._save()

    def _save(self):
        self.data["updatedAt"] = utc_now()
        atomic_write_json(self.journal_path, self.data)

    def replace(self, target, writer):
        target = ensure_within(self.managed_root, target)
        if not target.is_file():
            raise FileNotFoundError(target)
        index = len(self.data["actions"])
        rollback = self.rollback_dir / f"{index:04d}.rollback"
        shutil.copy2(target, rollback)
        action = {
            "target": str(target),
            "rollback": str(rollback),
            "before": file_signature(target),
            "after": None,
            "status": "prepared",
        }
        self.data["actions"].append(action)
        self._save()

        fd, temporary = tempfile.mkstemp(
            prefix=".joga-", suffix=".tmp", dir=str(target.parent)
        )
        os.close(fd)
        try:
            writer(temporary)
            if not os.path.isfile(temporary):
                raise OSError(f"Writer did not produce output for {target.name}")
            with open(temporary, "rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            action["after"] = file_signature(target)
            action["status"] = "applied"
            self._save()
        finally:
            try:
                os.unlink(temporary)
            except OSError:
                pass

    def commit(self):
        self.data["status"] = "committed"
        self._save()
        shutil.rmtree(self.rollback_dir, ignore_errors=True)

    def rollback(self):
        errors = []
        for action in reversed(self.data.get("actions", [])):
            rollback = Path(action["rollback"])
            target = Path(action["target"])
            if not rollback.is_file():
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(
                    prefix=".joga-rollback-", suffix=".tmp", dir=str(target.parent)
                )
                os.close(fd)
                shutil.copy2(rollback, temporary)
                os.replace(temporary, target)
                action["status"] = "rolled_back"
            except Exception as exc:
                errors.append(f"{target}: {exc}")
        self.data["status"] = "rollback_failed" if errors else "rolled_back"
        self.data["errors"] = errors
        self._save()
        if not errors:
            shutil.rmtree(self.rollback_dir, ignore_errors=True)
        return errors

    @staticmethod
    def recover_incomplete(journal_dir=None):
        journal_dir = Path(journal_dir or PATHS.transactions)
        recovered = []
        if not journal_dir.is_dir():
            return recovered
        for journal in journal_dir.glob("*.json"):
            data = read_json(journal, {}) or {}
            if data.get("status") not in {"active", "rollback_failed"}:
                continue
            errors = []
            for action in reversed(data.get("actions", [])):
                rollback = Path(action.get("rollback", ""))
                target = Path(action.get("target", ""))
                if not rollback.is_file() or not target.parent.is_dir():
                    continue
                try:
                    shutil.copy2(rollback, target)
                    action["status"] = "rolled_back"
                except Exception as exc:
                    errors.append(f"{target}: {exc}")
            data["status"] = "rollback_failed" if errors else "rolled_back"
            data["errors"] = errors
            data["updatedAt"] = utc_now()
            atomic_write_json(journal, data)
            if not errors:
                rollback_dir = journal_dir / f"{data.get('id', journal.stem)}.files"
                shutil.rmtree(rollback_dir, ignore_errors=True)
                recovered.append(data.get("id", journal.stem))
        return recovered
