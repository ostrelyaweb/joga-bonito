"""Quick smoke test for the refactored modules."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from joga_app.config import Config, VERSION, THUMBNAILS_DIR
from joga_app.catalog import Catalog
from joga_app.swap_backend import SwapBackend
from joga_app.i18n import t, set_language, get_language, available_languages
from joga_app.ui.theme import get_stylesheet

print("=== Module imports OK ===")

cfg = Config.load()
print(f"Config: theme={cfg.theme}, lang={cfg.language}, installs={len(cfg.installs)}, version={VERSION}")
print(f"Items DB: {cfg.items_db}")
print(f"Thumbnails dir: {THUMBNAILS_DIR}, exists={os.path.isdir(THUMBNAILS_DIR)}")

set_language("en")
print(f"EN: nav.swaps = {t('nav.swaps')}")
print(f"EN: swaps.compatible = {t('swaps.compatible', 'Wheel')}")

set_language("hr")
print(f"HR: nav.swaps = {t('nav.swaps')}")
print(f"HR: swaps.compatible = {t('swaps.compatible', 'Kotači')}")
print(f"Languages: {available_languages()}")

print(f"Theme QSS length: {len(get_stylesheet('dark'))} chars")

catalog = Catalog(cfg)
backend = SwapBackend(cfg)
print(f"Presets: {backend.presets.names()}")
print(f"Active swaps: {len(backend.presets.active_swaps())}")

history = SwapBackend.load_history()
print(f"History entries: {len(history)}")

print("\n=== All checks passed ===")
