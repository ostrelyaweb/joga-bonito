"""Deterministic builders; these never guess offsets or resize game files."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from joga_app.patches.manifest import FORMAT, FORMAT_VERSION, PatchManifest


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _base_manifest(
    target: Path, patch_id: str, name: str, author: str, kind: str, operations: list[dict]
) -> PatchManifest:
    payload = target.read_bytes()
    return PatchManifest.from_dict(
        {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "id": patch_id,
            "name": name,
            "author": author,
            "kind": kind,
            "target": {
                "file": target.name,
                "size": len(payload),
                "sha256": _sha256(payload),
            },
            "operations": operations,
        }
    )


def build_redirect_patch(
    target: str | Path,
    old_reference: str,
    new_reference: str,
    *,
    patch_id: str,
    name: str,
    author: str,
    encoding: str = "utf-8",
    offsets: Iterable[int] | None = None,
) -> PatchManifest:
    """Build an exact same-length reference replacement.

    If the reference occurs more than once, explicit offsets are required so the
    builder cannot silently choose the wrong asset reference.
    """
    target = Path(target)
    data = target.read_bytes()
    expected = old_reference.encode(encoding)
    replacement = new_reference.encode(encoding)
    if not expected or len(expected) != len(replacement):
        raise ValueError("Old and new encoded references must be non-empty and equal length")
    found = []
    start = 0
    while True:
        position = data.find(expected, start)
        if position < 0:
            break
        found.append(position)
        start = position + 1
    if offsets is None:
        if len(found) != 1:
            raise ValueError(f"Expected exactly one reference match, found {len(found)}")
        chosen = found
    else:
        chosen = list(offsets)
        if not chosen or any(position not in found for position in chosen):
            raise ValueError("Every explicit offset must point to the expected reference")
    operations = [
        {
            "offset": position,
            "expected": expected.hex(),
            "replacement": replacement.hex(),
            "label": f"{old_reference} -> {new_reference}",
        }
        for position in chosen
    ]
    return _base_manifest(target, patch_id, name, author, "redirect", operations)


def build_paint_patch(
    target: str | Path,
    offset: int,
    expected_color: bytes,
    replacement_color: bytes,
    *,
    patch_id: str,
    name: str,
    author: str,
) -> PatchManifest:
    """Build a color patch at an explicitly supplied, verified byte offset."""
    target = Path(target)
    data = target.read_bytes()
    if len(expected_color) not in {3, 4} or len(expected_color) != len(replacement_color):
        raise ValueError("Colors must be equal-length RGB or RGBA byte sequences")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("Paint offset must be a non-negative integer")
    if data[offset : offset + len(expected_color)] != expected_color:
        raise ValueError("Expected color is not present at the supplied offset")
    operation = {
        "offset": offset,
        "expected": expected_color.hex(),
        "replacement": replacement_color.hex(),
        "label": "Explicit RGB/RGBA paint value",
    }
    return _base_manifest(target, patch_id, name, author, "paint", [operation])
