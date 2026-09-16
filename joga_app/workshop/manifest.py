from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


FORMAT = "joga-bonito.workshop"
CATEGORIES = {"maps", "balls", "decals", "hud"}
ALLOWED_SUFFIXES = {".upk", ".tfc", ".bnk"}
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


class WorkshopValidationError(ValueError):
    pass


@dataclass(frozen=True)
class WorkshopFile:
    source: str
    target: str
    mode: str
    size: int
    sha256: str
    target_size: int | None = None
    target_sha256: str = ""

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise WorkshopValidationError("Each file entry must be an object")
        source = data.get("source", "")
        path = PurePosixPath(str(source).replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or len(path.parts) != 2 or path.parts[0] != "payload":
            raise WorkshopValidationError("File source must be payload/<filename>")
        target = data.get("target", "")
        if not isinstance(target, str) or Path(target).name != target or Path(target).suffix.lower() not in ALLOWED_SUFFIXES:
            raise WorkshopValidationError("File target must be a supported basename")
        mode = data.get("mode")
        if mode not in {"add", "replace"}:
            raise WorkshopValidationError("File mode must be add or replace")
        size = data.get("size")
        digest = str(data.get("sha256", "")).lower()
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or not _SHA.fullmatch(digest):
            raise WorkshopValidationError("Payload size or SHA-256 is invalid")
        target_size = data.get("targetSize")
        target_digest = str(data.get("targetSha256", "")).lower()
        if mode == "replace":
            if not isinstance(target_size, int) or target_size <= 0 or not _SHA.fullmatch(target_digest):
                raise WorkshopValidationError("Replace entries require targetSize and targetSha256")
        else:
            target_size, target_digest = None, ""
        return cls(str(path), target, mode, size, digest, target_size, target_digest)


@dataclass(frozen=True)
class WorkshopManifest:
    package_id: str
    name: str
    author: str
    category: str
    description: str
    files: tuple[WorkshopFile, ...]

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("format") != FORMAT or data.get("version") != 1:
            raise WorkshopValidationError("Unsupported Workshop manifest")
        package_id = data.get("id", "")
        if not isinstance(package_id, str) or not _ID.fullmatch(package_id):
            raise WorkshopValidationError("Invalid package id")
        name, author = data.get("name", ""), data.get("author", "")
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise WorkshopValidationError("Invalid package name")
        if not isinstance(author, str) or not author.strip() or len(author) > 120:
            raise WorkshopValidationError("Invalid package author")
        category = data.get("category")
        if category not in CATEGORIES:
            raise WorkshopValidationError("Unsupported package category")
        description = data.get("description", "")
        if not isinstance(description, str) or len(description) > 1000:
            raise WorkshopValidationError("Description is too long")
        raw_files = data.get("files")
        if not isinstance(raw_files, list) or not raw_files or len(raw_files) > 64:
            raise WorkshopValidationError("Package must contain 1-64 files")
        files = tuple(WorkshopFile.from_dict(item) for item in raw_files)
        sources = [item.source.casefold() for item in files]
        targets = [item.target.casefold() for item in files]
        if len(set(sources)) != len(sources) or len(set(targets)) != len(targets):
            raise WorkshopValidationError("Package contains duplicate source or target names")
        if sum(item.size for item in files) > 1024 * 1024 * 1024:
            raise WorkshopValidationError("Package payload exceeds 1 GB")
        return cls(package_id, name.strip(), author.strip(), category, description.strip(), files)
