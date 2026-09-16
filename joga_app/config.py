import os
import uuid

from joga_app.core.migrations import migrate_legacy_data
from joga_app.core.paths import PATHS, PROGRAM_DIR
from joga_app.core.storage import atomic_write_json, read_json

BASE_DIR = str(PROGRAM_DIR)
USER_DATA_DIR = str(PATHS.root)
SETTINGS_FILE = str(PATHS.config / "settings.json")
SWAPS_LOG_FILE = str(PATHS.data / "history.json")
PRESETS_FILE = str(PATHS.data / "presets.json")
GAME_SIG_FILE = str(PATHS.data / "game_sig.json")
BACKUPS_DIR = str(PATHS.backups)
TRANSACTIONS_DIR = str(PATHS.transactions)
THUMBNAILS_DIR = os.path.join(BASE_DIR, "assets", "thumbnails")
ITEM_ICONS_DIR = os.path.join(BASE_DIR, "assets", "item_icons")
DATA_DIR = os.path.join(BASE_DIR, "joga_data")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")
KEYS_FILE = os.path.join(DATA_DIR, "keys.txt")
VERSION = "1.1.0"

DEFAULT_INSTALLS = [
    {
        "name": "Epic",
        "source": "Epic",
        "cookedDir": r"D:\Farming Simulator 19\rocketleague\TAGame\CookedPCConsole",
    },
    {
        "name": "Steam",
        "source": "Steam",
        "cookedDir": r"D:\SteamLibrary\steamapps\common\rocketleague\TAGame\CookedPCConsole",
    },
]

DEFAULT_ITEMS_DB = os.path.join(DATA_DIR, "items.json")


class Config:
    def __init__(self, installs=None, items_db=None, theme="dark",
                 language="hr", auto_reapply=True):
        self.installs = installs if installs is not None else []
        self.items_db = items_db or DEFAULT_ITEMS_DB
        self.theme = theme
        self.language = language
        self.auto_reapply = auto_reapply

    @classmethod
    def load(cls, path=SETTINGS_FILE):
        PATHS.ensure()
        migrate_legacy_data()
        data = read_json(path, {}) or {}
        installs = data.get("installs")
        if not isinstance(installs, list) or not installs:
            installs = [dict(x) for x in DEFAULT_INSTALLS]
        items_db = data.get("itemsDb")
        if not items_db or not os.path.exists(items_db):
            items_db = DEFAULT_ITEMS_DB
        theme = data.get("theme", "dark")
        language = data.get("language", "hr")
        auto_reapply = data.get("autoReapply", True)
        config = cls(
            installs=installs,
            items_db=items_db,
            theme=theme,
            language=language,
            auto_reapply=auto_reapply,
        )
        config._normalise_installs()
        return config

    @staticmethod
    def _install_id(install):
        value = "|".join(
            [
                str(install.get("source", "")).strip().lower(),
                os.path.normcase(os.path.abspath(install.get("cookedDir", "") or "")),
            ]
        )
        return uuid.uuid5(uuid.NAMESPACE_URL, f"joga-bonito-install:{value}").hex

    def _normalise_installs(self):
        for install in self.installs:
            if not install.get("id"):
                install["id"] = self._install_id(install)

    def save(self, path=SETTINGS_FILE):
        PATHS.ensure()
        self._normalise_installs()
        data = {
            "installs": self.installs,
            "itemsDb": self.items_db,
            "theme": self.theme,
            "language": self.language,
            "autoReapply": self.auto_reapply,
        }
        atomic_write_json(path, data)

    def get_install(self, name):
        for inst in self.installs:
            if inst.get("name") == name or inst.get("id") == name:
                return inst
        return None
