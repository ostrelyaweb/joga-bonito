import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
SWAPS_LOG_FILE = os.path.join(BASE_DIR, "swaps.json")
PRESETS_FILE = os.path.join(BASE_DIR, "presets.json")
GAME_SIG_FILE = os.path.join(BASE_DIR, "game_sig.json")
BACKUPS_DIR = os.path.join(BASE_DIR, "Backups")
THUMBNAILS_DIR = os.path.join(BASE_DIR, "assets", "thumbnails")
ITEM_ICONS_DIR = os.path.join(BASE_DIR, "assets", "item_icons")
DATA_DIR = os.path.join(BASE_DIR, "joga_data")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")
KEYS_FILE = os.path.join(DATA_DIR, "keys.txt")
VERSION = "1.0.0"

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
        data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        installs = data.get("installs")
        if not isinstance(installs, list) or not installs:
            installs = [dict(x) for x in DEFAULT_INSTALLS]
        items_db = data.get("itemsDb")
        if not items_db or not os.path.exists(items_db):
            items_db = DEFAULT_ITEMS_DB
        theme = data.get("theme", "dark")
        language = data.get("language", "hr")
        auto_reapply = data.get("autoReapply", True)
        return cls(
            installs=installs,
            items_db=items_db,
            theme=theme,
            language=language,
            auto_reapply=auto_reapply,
        )

    def save(self, path=SETTINGS_FILE):
        data = {
            "installs": self.installs,
            "itemsDb": self.items_db,
            "theme": self.theme,
            "language": self.language,
            "autoReapply": self.auto_reapply,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_install(self, name):
        for inst in self.installs:
            if inst.get("name") == name:
                return inst
        return None
