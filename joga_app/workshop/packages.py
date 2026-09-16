from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from joga_app.core.paths import PATHS
from joga_app.workshop.manifest import WorkshopManifest, WorkshopValidationError


class WorkshopImportError(ValueError):
    pass


class WorkshopImporter:
    def __init__(self, root=None):
        self.root = Path(root or PATHS.workshop)

    def import_package(self, archive_path):
        archive_path = Path(archive_path)
        if archive_path.suffix.lower() != ".jbworkshop":
            raise WorkshopImportError("Expected a .jbworkshop package")
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                entries = [item for item in archive.infolist() if not item.is_dir()]
                if not entries or len(entries) > 72:
                    raise WorkshopImportError("Invalid package file count")
                paths = []
                for item in entries:
                    path = PurePosixPath(item.filename.replace("\\", "/"))
                    if path.is_absolute() or ".." in path.parts:
                        raise WorkshopImportError("Package contains an unsafe path")
                    paths.append(path)
                if PurePosixPath("manifest.json") not in paths:
                    raise WorkshopImportError("Package is missing manifest.json")
                with archive.open("manifest.json") as handle:
                    manifest = WorkshopManifest.from_dict(json.load(handle))
                allowed = {PurePosixPath("manifest.json"), *(PurePosixPath(f.source) for f in manifest.files)}
                allowed.update(path for path in paths if len(path.parts) == 1 and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
                if set(paths) != allowed:
                    raise WorkshopImportError("Package contains undeclared or unsupported files")
                by_path = {path: item for path, item in zip(paths, entries)}
                for file in manifest.files:
                    item = by_path[PurePosixPath(file.source)]
                    if item.file_size != file.size:
                        raise WorkshopImportError(f"Size mismatch: {file.source}")
                    digest = hashlib.sha256()
                    with archive.open(item) as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            digest.update(chunk)
                    if digest.hexdigest() != file.sha256:
                        raise WorkshopImportError(f"SHA-256 mismatch: {file.source}")
                destination = self.root / manifest.category / manifest.package_id
                if destination.exists():
                    raise WorkshopImportError("Package id is already imported")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix=".workshop-", dir=str(destination.parent)) as temporary:
                    stage = Path(temporary) / "package"
                    stage.mkdir()
                    for path, item in zip(paths, entries):
                        output = stage.joinpath(*path.parts)
                        output.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(item) as source, output.open("wb") as target:
                            shutil.copyfileobj(source, target)
                    stage.replace(destination)
                return manifest, destination
        except (zipfile.BadZipFile, OSError, ValueError, KeyError, WorkshopValidationError) as exc:
            if isinstance(exc, WorkshopImportError):
                raise
            raise WorkshopImportError(str(exc)) from exc

    def list_packages(self):
        result = []
        for path in self.root.glob("*/*/manifest.json") if self.root.is_dir() else ():
            try:
                result.append((WorkshopManifest.from_dict(json.loads(path.read_text(encoding="utf-8"))), path.parent))
            except (OSError, ValueError, WorkshopValidationError):
                continue
        return sorted(result, key=lambda item: (item[0].category, item[0].name.casefold()))
