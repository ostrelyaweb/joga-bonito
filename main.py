import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from joga_app.catalog import Catalog
from joga_app.config import BASE_DIR, Config
from joga_app.swap_backend import SwapBackend
from joga_app.ui.main_window import MainWindow


ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.png")


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    cfg = Config.load()
    catalog = Catalog(cfg)
    backend = SwapBackend(cfg)
    window = MainWindow(cfg, catalog, backend)
    window.setWindowIcon(QIcon(ICON_PATH))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
