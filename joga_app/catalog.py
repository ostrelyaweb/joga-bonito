import json
import os

SLOT_PREFIXES = [
    ("WHEEL_", "Wheel"),
    ("Boost_", "Boost"),
    ("Body_", "Body"),
    ("Decal_", "Decal"),
    ("Antenna_", "Antenna"),
    ("Topper_", "Topper"),
    ("Trail_", "Trail"),
    ("Banner_", "Banner"),
    ("AvatarBorder_", "Avatar Border"),
    ("GoalExplosion_", "Goal Explosion"),
    ("EngineAudio_", "Engine Audio"),
    ("Anthem_", "Anthem"),
    ("album_anthem_", "Anthem"),
    ("RocketBoost_", "Rocket Boost"),
    ("Ball_", "Ball"),
]

EXCLUDED_STARTS = [
    "BG_", "Beach_", "Stadium", "Labs", "Classic_", "Utopia_", "Aquadome",
    "Champions_", "Manfield", "DFH_", "EuroStadium", "Wasteland", "Farmstead",
    "Underpass", "NeoTokyo_", "Salty_", "Arc_", "Training_", "Mutator",
]

_EXCLUDED_UPPER = tuple(s.upper() for s in EXCLUDED_STARTS)


class CatalogItem:
    def __init__(self, file, label, category, quality=""):
        self.file = file
        self.label = label
        self.category = category
        self.quality = quality

    def display(self):
        if self.quality:
            return f"{self.category} — {self.label} ({self.quality})  [{self.file}]"
        return f"{self.category} — {self.label}  [{self.file}]"

    def to_dict(self):
        return {
            "file": self.file,
            "label": self.label,
            "category": self.category,
            "quality": self.quality,
        }


class Catalog:
    def __init__(self, cfg):
        self.cfg = cfg
        self._db = None

    def _load_db(self):
        if self._db is not None:
            return self._db
        db = {}
        path = self.cfg.items_db
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                for e in entries:
                    name = e.get("AssetPackageName")
                    if not name:
                        continue
                    db[name] = {
                        "label": e.get("Product") or name,
                        "category": e.get("Slot") or "Other",
                        "quality": e.get("Quality") or "",
                    }
            except Exception:
                db = {}
        self._db = db
        return db

    def items_for_install(self, install):
        db = self._load_db()
        result = {}
        cooked = install.get("cookedDir")
        if not cooked or not os.path.isdir(cooked):
            return result
        try:
            names = os.listdir(cooked)
        except OSError:
            return result
        for fn in names:
            if not fn.lower().endswith(".upk"):
                continue
            bare = fn[:-4]
            if bare.upper().startswith(_EXCLUDED_UPPER):
                continue
            asset = bare
            if asset.endswith("_SF"):
                asset = asset[:-3]
            info = db.get(asset)
            if info is not None:
                item = CatalogItem(
                    file=fn,
                    label=info["label"],
                    category=info["category"],
                    quality=info["quality"],
                )
            else:
                category = None
                upp = asset.upper()
                for prefix, label in SLOT_PREFIXES:
                    if upp.startswith(prefix.upper()):
                        category = label
                        break
                if category is None:
                    continue
                display = asset.replace("_", " ").strip()
                item = CatalogItem(file=fn, label=display, category=category)
            result[fn] = item
        return result

    def grouped(self, install):
        items = self.items_for_install(install)
        groups = {}
        for it in items.values():
            groups.setdefault(it.category, []).append(it)
        for g in groups.values():
            g.sort(key=lambda x: x.label.lower())
        return groups

    def flat(self, install):
        groups = self.grouped(install)
        flat = []
        for cat in sorted(groups):
            flat.extend(groups[cat])
        return flat