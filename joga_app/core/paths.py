import os
from dataclasses import dataclass
from pathlib import Path


PROGRAM_DIR = Path(__file__).resolve().parents[2]


def _default_user_root() -> Path:
    override = os.environ.get("JOGA_BONITO_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        return (Path(appdata) / "JogaBonito").resolve()
    return (Path.home() / "AppData" / "Roaming" / "JogaBonito").resolve()


@dataclass(frozen=True)
class PathLayout:
    root: Path

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def transactions(self) -> Path:
        return self.root / "transactions"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def packages(self) -> Path:
        return self.root / "packages"

    @property
    def workshop(self) -> Path:
        return self.root / "workshop"

    @property
    def updates(self) -> Path:
        return self.root / "updates"

    def ensure(self) -> None:
        directories = (
            self.root,
            self.config,
            self.data,
            self.backups,
            self.transactions,
            self.logs,
            self.packages / "balls",
            self.packages / "decals",
            self.packages / "hud",
            self.packages / "patches",
            self.workshop,
            self.updates,
        )
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


PATHS = PathLayout(_default_user_root())
