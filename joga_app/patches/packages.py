"""Safe importer for .jbpkg ZIP containers."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from joga_app.core.paths import PATHS
from joga_app.patches.manifest import PatchManifest, PatchValidationError


MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_FILES = 32
ALLOWED_FILES = {".json", ".png", ".jpg", ".jpeg", ".webp"}


class PackageImportError(ValueError):
    pass


class PackageImporter:
    def __init__(self, package_root: str | Path | None = None):
        self.package_root = Path(package_root or (PATHS.packages / "patches"))

    @staticmethod
    def _safe_members(archive: zipfile.ZipFile):
        members = [item for item in archive.infolist() if not item.is_dir()]
        if not members or len(members) > MAX_PACKAGE_FILES:
            raise PackageImportError("Package has an invalid file count")
        if sum(item.file_size for item in members) > MAX_PACKAGE_BYTES:
            raise PackageImportError("Package is larger than 16 MB")
        for item in members:
            path = PurePosixPath(item.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise PackageImportError("Package contains an unsafe path")
            if path.suffix.lower() not in ALLOWED_FILES:
                raise PackageImportError(f"Package file type is not allowed: {path.suffix}")
            yield item, path

    def import_package(self, package_path: str | Path) -> tuple[PatchManifest, Path]:
        package_path = Path(package_path)
        if package_path.suffix.lower() != ".jbpkg":
            raise PackageImportError("Expected a .jbpkg package")
        self.package_root.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(package_path, "r") as archive:
                safe_members = list(self._safe_members(archive))
                manifest_entry = next(
                    (item for item, path in safe_members if path == PurePosixPath("manifest.json")),
                    None,
                )
                if manifest_entry is None:
                    raise PackageImportError("Package is missing root manifest.json")
                with archive.open(manifest_entry) as handle:
                    import json

                    manifest = PatchManifest.from_dict(json.load(handle))
                destination = self.package_root / manifest.patch_id
                if destination.exists():
                    raise PackageImportError("A package with this id is already installed")
                with tempfile.TemporaryDirectory(
                    prefix=".jbpkg-", dir=str(self.package_root)
                ) as temporary:
                    stage = Path(temporary) / "payload"
                    stage.mkdir()
                    for item, relative in safe_members:
                        output = stage.joinpath(*relative.parts)
                        output.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(item) as source, output.open("wb") as target:
                            shutil.copyfileobj(source, target)
                    stage.replace(destination)
                return manifest, destination
        except (zipfile.BadZipFile, OSError, ValueError, PatchValidationError) as exc:
            if isinstance(exc, PackageImportError):
                raise
            raise PackageImportError(str(exc)) from exc

    def list_manifests(self) -> list[tuple[PatchManifest, Path]]:
        result = []
        if not self.package_root.is_dir():
            return result
        for manifest_path in self.package_root.glob("*/manifest.json"):
            try:
                result.append((PatchManifest.from_file(manifest_path), manifest_path.parent))
            except PatchValidationError:
                continue
        return sorted(result, key=lambda item: item[0].name.casefold())
