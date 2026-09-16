import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from joga_app.update.client import UpdateClient, UpdateError
from joga_app.update.manifest import canonical_bytes, verify_envelope


def signed_envelope(package=b"installer", version="9.0.0"):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    signed = {
        "format": "joga-bonito.update",
        "schema": 1,
        "appVersion": version,
        "notes": "Test release",
        "package": {
            "type": "installer",
            "url": "https://example.invalid/JogaBonito.exe",
            "size": len(package),
            "sha256": hashlib.sha256(package).hexdigest(),
        },
    }
    envelope = {"signed": signed, "signature": base64.b64encode(private.sign(canonical_bytes(signed))).decode()}
    return envelope, base64.b64encode(public).decode()


class FakeResponse:
    def __init__(self, data, url="https://example.invalid/file"):
        self.data, self.url, self.offset = data, url, 0
    def geturl(self): return self.url
    def read(self, size=-1):
        if size < 0: size = len(self.data) - self.offset
        chunk = self.data[self.offset:self.offset + size]; self.offset += len(chunk); return chunk
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, *_args): self.close()


class UpdateSecurityTests(unittest.TestCase):
    def test_signature_verification_and_tamper_rejection(self):
        envelope, public = signed_envelope()
        manifest = verify_envelope(envelope, public)
        self.assertTrue(manifest.is_newer_than("1.5.0"))
        envelope["signed"]["appVersion"] = "9.0.1"
        with self.assertRaises(ValueError): verify_envelope(envelope, public)

    def test_download_requires_signed_size_and_hash(self):
        package = b"verified-installer"
        envelope, public = signed_envelope(package)
        manifest = verify_envelope(envelope, public)
        with tempfile.TemporaryDirectory() as temporary:
            client = UpdateClient(staging_root=temporary, opener=lambda *_args, **_kwargs: FakeResponse(package))
            path = client.download(manifest)
            self.assertEqual(path.read_bytes(), package)
            bad = UpdateClient(staging_root=Path(temporary) / "bad", opener=lambda *_args, **_kwargs: FakeResponse(package + b"tampered"))
            with self.assertRaises(UpdateError): bad.download(manifest)

    def test_manifest_client_rejects_non_https_redirect(self):
        envelope, _public = signed_envelope()
        payload = json.dumps(envelope).encode()
        client = UpdateClient(opener=lambda *_args, **_kwargs: FakeResponse(payload, "http://unsafe.invalid/manifest"))
        with self.assertRaises(UpdateError): client.check()


if __name__ == "__main__": unittest.main()
