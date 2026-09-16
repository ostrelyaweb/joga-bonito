"""Independent local Rocket League thumbnail resolver for Joga Bonito."""

import os
import re

from PySide6.QtCore import QObject, Signal

from joga_app.config import ITEM_ICONS_DIR


def package_key(value: str) -> str:
    """Return the local artwork filename for a Rocket League package."""
    stem = os.path.splitext(os.path.basename(value or ""))[0]
    for suffix in ("_T_SF", "_SF"):
        if stem.upper().endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    stem = re.sub(r"[^A-Za-z0-9_-]", "", stem).strip("_").lower()
    return stem


class ThumbnailProvider(QObject):
    thumbnail_ready = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        os.makedirs(ITEM_ICONS_DIR, exist_ok=True)

    def cached_path(self, package_name: str) -> str:
        key = package_key(package_name)
        if not key:
            return ""
        for extension in ("webp", "png", "jpg", "jpeg"):
            path = os.path.join(ITEM_ICONS_DIR, f"{key}.{extension}")
            if os.path.isfile(path):
                return path
        return ""

    def request(self, package_name: str):
        """Compatibility hook: all artwork is bundled, so no network is used."""
        return
