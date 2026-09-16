from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from joga_app.config import VERSION
from joga_app.core.paths import PATHS
from joga_app.update.manifest import verify_envelope


DEFAULT_MANIFEST_URL = "https://raw.githubusercontent.com/ostrelyaweb/joga-bonito/main/releases/stable.json"


class UpdateError(RuntimeError):
    pass


class UpdateClient:
    def __init__(self, manifest_url=DEFAULT_MANIFEST_URL, staging_root=None, opener=None):
        if not manifest_url.startswith("https://"):
            raise ValueError("Manifest URL must use HTTPS")
        self.manifest_url = manifest_url
        self.staging_root = Path(staging_root or PATHS.updates)
        self.opener = opener or urllib.request.urlopen

    def _open(self, url, timeout=15):
        request = urllib.request.Request(url, headers={"User-Agent": f"JogaBonito/{VERSION}"})
        response = self.opener(request, timeout=timeout)
        if not response.geturl().startswith("https://"):
            response.close()
            raise UpdateError("Update redirect left HTTPS")
        return response

    def check(self):
        try:
            with self._open(self.manifest_url, 10) as response:
                payload = response.read(1024 * 1024 + 1)
            if len(payload) > 1024 * 1024:
                raise UpdateError("Update manifest is too large")
            return verify_envelope(json.loads(payload.decode("utf-8")))
        except UpdateError:
            raise
        except Exception as exc:
            raise UpdateError(f"Update check failed: {exc}") from exc

    def download(self, manifest):
        folder = self.staging_root / manifest.version
        folder.mkdir(parents=True, exist_ok=True)
        suffix = ".exe" if manifest.package_type == "installer" else ".zip"
        destination = folder / f"JogaBonito-{manifest.version}{suffix}"
        temporary = destination.with_suffix(destination.suffix + ".download")
        digest, total = hashlib.sha256(), 0
        try:
            with self._open(manifest.url, 30) as response, temporary.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    total += len(chunk)
                    if total > manifest.size: raise UpdateError("Downloaded package exceeds signed size")
                    digest.update(chunk); output.write(chunk)
                output.flush(); os.fsync(output.fileno())
            if total != manifest.size or digest.hexdigest() != manifest.sha256:
                raise UpdateError("Downloaded package failed signed size or SHA-256 verification")
            os.replace(temporary, destination)
            return destination
        except Exception as exc:
            try: temporary.unlink()
            except OSError: pass
            if isinstance(exc, UpdateError): raise
            raise UpdateError(f"Update download failed: {exc}") from exc

    @staticmethod
    def launch_installer(path):
        path = Path(path)
        if path.suffix.lower() != ".exe" or not path.is_file():
            raise UpdateError("Verified installer is missing")
        subprocess.Popen([str(path)], close_fds=True)
