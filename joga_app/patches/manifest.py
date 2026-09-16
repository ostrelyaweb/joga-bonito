"""Schema and strict validation for independent Joga Bonito patch manifests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FORMAT = "joga-bonito.patch"
FORMAT_VERSION = 1
ALLOWED_KINDS = {"redirect", "paint"}
ALLOWED_TARGET_SUFFIXES = {".upk", ".bnk"}
MAX_OPERATIONS = 4096
MAX_PATCHED_BYTES = 8 * 1024 * 1024
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class PatchValidationError(ValueError):
    pass


def _decode_hex(value: Any, field: str) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or len(value) % 2
        or re.fullmatch(r"[0-9a-fA-F]+", value) is None
    ):
        raise PatchValidationError(f"{field} must be non-empty, even-length hex")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise PatchValidationError(f"{field} is not valid hex") from exc


@dataclass(frozen=True)
class PatchOperation:
    offset: int
    expected: bytes
    replacement: bytes
    label: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatchOperation":
        if not isinstance(data, dict):
            raise PatchValidationError("Each operation must be an object")
        offset = data.get("offset")
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise PatchValidationError("operation.offset must be a non-negative integer")
        expected = _decode_hex(data.get("expected"), "operation.expected")
        replacement = _decode_hex(data.get("replacement"), "operation.replacement")
        if len(expected) != len(replacement):
            raise PatchValidationError("Expected and replacement byte lengths must match")
        label = data.get("label", "")
        if not isinstance(label, str) or len(label) > 160:
            raise PatchValidationError("operation.label must be at most 160 characters")
        return cls(offset, expected, replacement, label)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "offset": self.offset,
            "expected": self.expected.hex(),
            "replacement": self.replacement.hex(),
        }
        if self.label:
            result["label"] = self.label
        return result


@dataclass(frozen=True)
class PatchManifest:
    patch_id: str
    name: str
    author: str
    kind: str
    target_file: str
    target_size: int
    target_sha256: str
    operations: tuple[PatchOperation, ...]
    description: str = ""
    output_sha256: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatchManifest":
        if not isinstance(data, dict):
            raise PatchValidationError("Manifest root must be an object")
        if data.get("format") != FORMAT or data.get("version") != FORMAT_VERSION:
            raise PatchValidationError("Unsupported patch format or version")
        patch_id = data.get("id")
        if not isinstance(patch_id, str) or not _ID_RE.fullmatch(patch_id):
            raise PatchValidationError("Invalid patch id")
        name = data.get("name")
        author = data.get("author")
        kind = data.get("kind")
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise PatchValidationError("Patch name is required and limited to 120 characters")
        if not isinstance(author, str) or not author.strip() or len(author) > 120:
            raise PatchValidationError("Patch author is required and limited to 120 characters")
        if kind not in ALLOWED_KINDS:
            raise PatchValidationError("Patch kind must be redirect or paint")

        target = data.get("target")
        if not isinstance(target, dict):
            raise PatchValidationError("target must be an object")
        target_file = target.get("file")
        if (
            not isinstance(target_file, str)
            or not target_file
            or Path(target_file).name != target_file
            or Path(target_file).suffix.lower() not in ALLOWED_TARGET_SUFFIXES
        ):
            raise PatchValidationError("target.file must be a .upk or .bnk basename")
        target_size = target.get("size")
        if not isinstance(target_size, int) or isinstance(target_size, bool) or target_size <= 0:
            raise PatchValidationError("target.size must be a positive integer")
        target_sha256 = target.get("sha256")
        if not isinstance(target_sha256, str) or not _SHA_RE.fullmatch(target_sha256.lower()):
            raise PatchValidationError("target.sha256 must be a 64-character SHA-256")

        raw_ops = data.get("operations")
        if not isinstance(raw_ops, list) or not raw_ops or len(raw_ops) > MAX_OPERATIONS:
            raise PatchValidationError(f"operations must contain 1-{MAX_OPERATIONS} entries")
        operations = tuple(PatchOperation.from_dict(item) for item in raw_ops)
        if sum(len(item.expected) for item in operations) > MAX_PATCHED_BYTES:
            raise PatchValidationError("Patch payload is too large")
        ordered = sorted(operations, key=lambda item: item.offset)
        previous_end = -1
        for operation in ordered:
            end = operation.offset + len(operation.expected)
            if end > target_size:
                raise PatchValidationError("Patch operation extends beyond target size")
            if operation.offset < previous_end:
                raise PatchValidationError("Patch operations may not overlap")
            previous_end = end

        description = data.get("description", "")
        if not isinstance(description, str) or len(description) > 1000:
            raise PatchValidationError("description must be at most 1000 characters")
        output_sha256 = target.get("outputSha256", "")
        if output_sha256 and (
            not isinstance(output_sha256, str) or not _SHA_RE.fullmatch(output_sha256.lower())
        ):
            raise PatchValidationError("target.outputSha256 must be a SHA-256")
        return cls(
            patch_id,
            name.strip(),
            author.strip(),
            kind,
            target_file,
            target_size,
            target_sha256.lower(),
            operations,
            description.strip(),
            output_sha256.lower() if output_sha256 else "",
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "PatchManifest":
        try:
            with Path(path).open("r", encoding="utf-8") as handle:
                return cls.from_dict(json.load(handle))
        except (OSError, json.JSONDecodeError) as exc:
            raise PatchValidationError(f"Cannot read manifest: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        target = {
            "file": self.target_file,
            "size": self.target_size,
            "sha256": self.target_sha256,
        }
        if self.output_sha256:
            target["outputSha256"] = self.output_sha256
        return {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "id": self.patch_id,
            "name": self.name,
            "author": self.author,
            "kind": self.kind,
            "description": self.description,
            "target": target,
            "operations": [operation.to_dict() for operation in self.operations],
        }
