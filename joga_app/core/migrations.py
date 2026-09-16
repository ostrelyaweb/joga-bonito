import shutil
from pathlib import Path

from joga_app.core.paths import PATHS, PROGRAM_DIR, PathLayout
from joga_app.core.storage import atomic_write_json, read_json


MIGRATION_VERSION = 1


def migrate_legacy_data(
    program_dir: Path = PROGRAM_DIR, layout: PathLayout = PATHS
) -> dict:
    """Copy legacy mutable state to AppData once, without overwriting user data."""
    program_dir = Path(program_dir)
    layout.ensure()
    marker = layout.root / ".migration-v1.json"
    previous = read_json(marker, {}) or {}
    if previous.get("version", 0) >= MIGRATION_VERSION:
        return previous

    copied = []
    mappings = {
        "settings.json": layout.config / "settings.json",
        "presets.json": layout.data / "presets.json",
        "swaps.json": layout.data / "history.json",
        "game_sig.json": layout.data / "game_sig.json",
    }
    for legacy_name, destination in mappings.items():
        source = program_dir / legacy_name
        if source.is_file() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(legacy_name)

    legacy_backups = program_dir / "Backups"
    if legacy_backups.is_dir() and not any(layout.backups.iterdir()):
        for child in legacy_backups.iterdir():
            destination = layout.backups / child.name
            if child.is_dir():
                shutil.copytree(child, destination, dirs_exist_ok=False)
            elif child.is_file():
                shutil.copy2(child, destination)
        copied.append("Backups")

    result = {"version": MIGRATION_VERSION, "copied": copied}
    atomic_write_json(marker, result)
    return result
