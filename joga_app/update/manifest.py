from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


PUBLIC_KEY_B64 = "RSDvshZSd3/USQ2cqHIeN7LVtjNNPbPZOP9pHLqkWJI="
_SHA = re.compile(r"^[0-9a-f]{64}$")


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def version_tuple(value):
    parts = str(value).split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("Version must use major.minor.patch")
    return tuple(int(part) for part in parts)


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    notes: str
    url: str
    size: int
    sha256: str
    package_type: str

    @classmethod
    def from_signed(cls, data):
        if not isinstance(data, dict) or data.get("format") != "joga-bonito.update" or data.get("schema") != 1:
            raise ValueError("Unsupported update manifest")
        version = data.get("appVersion", ""); version_tuple(version)
        notes = data.get("notes", "")
        package = data.get("package", {})
        url, size, digest, kind = package.get("url", ""), package.get("size"), str(package.get("sha256", "")).lower(), package.get("type")
        if not isinstance(notes, str) or len(notes) > 10000:
            raise ValueError("Invalid release notes")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError("Update package must use HTTPS")
        if not isinstance(size, int) or size <= 0 or size > 1024 * 1024 * 1024:
            raise ValueError("Invalid update package size")
        if not _SHA.fullmatch(digest) or kind not in {"installer", "portable"}:
            raise ValueError("Invalid update package metadata")
        return cls(version, notes, url, size, digest, kind)

    def is_newer_than(self, current):
        return version_tuple(self.version) > version_tuple(current)


def verify_envelope(envelope, public_key_b64=PUBLIC_KEY_B64):
    if not isinstance(envelope, dict) or set(envelope) != {"signed", "signature"}:
        raise ValueError("Invalid signed update envelope")
    signed, signature_text = envelope["signed"], envelope["signature"]
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64, validate=True))
        signature = base64.b64decode(signature_text, validate=True)
        key.verify(signature, canonical_bytes(signed))
    except (ValueError, InvalidSignature) as exc:
        raise ValueError("Update manifest signature is invalid") from exc
    return UpdateManifest.from_signed(signed)
