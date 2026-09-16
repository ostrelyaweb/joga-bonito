import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget,
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QDialogButtonBox, QFrame,
)
from PySide6.QtCore import QTimer, Qt, QPoint
from PySide6.QtGui import QIcon, QPixmap

from joga_app.ui.swaps_page import SwapsPage
from joga_app.ui.patches_page import PatchesPage
from joga_app.ui.overlays_page import OverlaysPage
from joga_app.ui.workshop_page import WorkshopPage
from joga_app.ui.presets_page import PresetsPage
from joga_app.ui.history_page import HistoryPage
from joga_app.ui.settings_page import SettingsPage
from joga_app.ui.sidebar import Sidebar
from joga_app.ui.theme import get_stylesheet
from joga_app.i18n import t, set_language
from joga_app.config import BASE_DIR, VERSION
from joga_app.patches import PatchService
from joga_app.overlays import OverlayManager
from joga_app.workshop import WorkshopService


ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.png")


class TitleBar(QFrame):
    """Compact branded window chrome with native-feeling window controls."""

    def __init__(self, parent):
        super().__init__(parent)
        self._drag_offset = QPoint()
        self.setObjectName("titleBar")
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(8)

        mark = QLabel()
        mark.setObjectName("titleBarMark")
        if os.path.exists(ICON_PATH):
            mark.setPixmap(QPixmap(ICON_PATH).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(mark)

        title = QLabel("JOGA BONITO")
        title.setObjectName("titleBarTitle")
        layout.addWidget(title)

        context = QLabel("Rocket League cosmetics")
        context.setObjectName("titleBarContext")
        layout.addWidget(context)
        layout.addStretch()

        self.minimize_btn = QPushButton("—")
        self.minimize_btn.setObjectName("windowControl")
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.clicked.connect(parent.showMinimized)
        layout.addWidget(self.minimize_btn)

        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setObjectName("windowControl")
        self.maximize_btn.setToolTip("Maximize")
        self.maximize_btn.clicked.connect(self._toggle_maximized)
        layout.addWidget(self.maximize_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("windowClose")
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(parent.close)
        layout.addWidget(close_btn)

    def _toggle_maximized(self):
        window = self.window()
        if window.isMaximized():
            window.showNormal()
            self.maximize_btn.setText("□")
        else:
            window.showMaximized()
            self.maximize_btn.setText("❐")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_maximized()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self.window().isMaximized():
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)


class InstallDialog(QDialog):
    """Add / edit a game installation."""

    def __init__(self, parent=None, install=None):
        super().__init__(parent)
        self.setWindowTitle(t("dlg.install_title"))
        self.setMinimumWidth(520)

        self.name_edit = QLineEdit()
        self.source_edit = QLineEdit()
        self.dir_edit = QLineEdit()
        browse = QPushButton(t("settings.browse"))
        browse.clicked.connect(self._browse)

        form = QFormLayout()
        form.addRow(t("dlg.name"), self.name_edit)
        form.addRow(t("dlg.source"), self.source_edit)

        row = QHBoxLayout()
        row.addWidget(self.dir_edit)
        row.addWidget(browse)
        form.addRow(t("dlg.cooked"), row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if install:
            self.name_edit.setText(install.get("name", ""))
            self.source_edit.setText(install.get("source", ""))
            self.dir_edit.setText(install.get("cookedDir", ""))

    def _browse(self):
        current = self.dir_edit.text()
        start = current if current and os.path.isdir(current) else os.path.dirname(current)
        folder = QFileDialog.getExistingDirectory(self, t("dlg.browse"), start)
        if folder:
            self.dir_edit.setText(folder)

    def values(self):
        return {
            "name": self.name_edit.text().strip(),
            "source": self.source_edit.text().strip() or "Steam",
            "cookedDir": self.dir_edit.text().strip(),
        }


class MainWindow(QMainWindow):
    def __init__(self, cfg, catalog, backend):
        super().__init__()
        self.cfg = cfg
        self.catalog = catalog
        self.backend = backend

        self.setWindowTitle("Joga Bonito — Rocket League Cosmetics")
        self.resize(1220, 780)
        self.setMinimumSize(1080, 680)
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)

        # Apply language & theme
        set_language(self.cfg.language)
        self.setStyleSheet(get_stylesheet(self.cfg.theme))

        # --- Central widget ---
        central = QWidget()
        self.setCentralWidget(central)
        shell_layout = QVBoxLayout(central)
        shell_layout.setContentsMargins(1, 1, 1, 1)
        shell_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        shell_layout.addWidget(self.title_bar)

        body = QWidget()
        body.setObjectName("windowBody")
        main_layout = QHBoxLayout(body)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        shell_layout.addWidget(body, 1)

        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # Stacked content area
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        main_layout.addWidget(self.stack, 1)

        # Pages
        self.swaps_page = SwapsPage(self.cfg, self.catalog, self.backend)
        self.patch_service = PatchService()
        self.patches_page = PatchesPage(self.cfg, self.patch_service)
        self.overlay_manager = OverlayManager(parent=self)
        self.overlays_page = OverlaysPage(self.cfg, self.overlay_manager)
        self.workshop_service = WorkshopService()
        self.workshop_page = WorkshopPage(self.cfg, self.workshop_service)
        self.presets_page = PresetsPage(self.cfg, self.catalog, self.backend)
        self.history_page = HistoryPage(self.cfg, self.catalog, self.backend)
        self.settings_page = SettingsPage(self.cfg, self.catalog, self.backend)

        self.pages = [
            self.swaps_page,
            self.patches_page,
            self.overlays_page,
            self.workshop_page,
            self.presets_page,
            self.history_page,
            self.settings_page,
        ]
        for page in self.pages:
            self.stack.addWidget(page)

        # Connect sidebar signals
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.sidebar.install_changed.connect(self._on_install_changed)

        # Connect settings signals
        if hasattr(self.settings_page, "theme_changed"):
            self.settings_page.theme_changed.connect(self.apply_theme)
        if hasattr(self.settings_page, "language_changed"):
            self.settings_page.language_changed.connect(self.apply_language)
        if hasattr(self.settings_page, "installs_changed"):
            self.settings_page.installs_changed.connect(self._on_installs_changed)

        # Populate sidebar
        self.sidebar.set_installs(self.cfg.installs)

        # Status bar
        if self.backend.recovered_transactions:
            self.statusBar().showMessage(
                t("msg.transactions_recovered", len(self.backend.recovered_transactions)),
                12000,
            )
        else:
            self.statusBar().showMessage(t("msg.ready"))
        self.statusBar().messageChanged.connect(self._on_status_message)

        # Canary drift check
        QTimer.singleShot(0, self._run_canary)

    # ------------------------------------------------------------------

    def _on_page_changed(self, index):
        self.stack.setCurrentIndex(index)
        page = self.pages[index]
        if hasattr(page, "refresh"):
            page.refresh()

    def _on_install_changed(self):
        install = self.sidebar.current_install()
        if install:
            for page in self.pages:
                if hasattr(page, "set_install"):
                    page.set_install(install)

    def closeEvent(self, event):
        self.overlay_manager.shutdown()
        super().closeEvent(event)

    def _on_installs_changed(self):
        """Re-sync sidebar when the installs list is modified in Settings."""
        self.sidebar.set_installs(self.cfg.installs)

    def _on_status_message(self, message):
        if message and hasattr(self, "overlay_manager"):
            self.overlay_manager.notify(message)

    def _run_canary(self):
        results = self.backend.check_for_drift()
        if results:
            QMessageBox.information(
                self,
                t("msg.canary_title"),
                t("msg.canary_drift", "\n".join(results)),
            )
        else:
            self.statusBar().showMessage(t("msg.canary_ok"))

    def apply_theme(self, theme):
        self.cfg.theme = theme
        self.cfg.save()
        self.setStyleSheet(get_stylesheet(theme))

    def apply_language(self, lang):
        self.cfg.language = lang
        self.cfg.save()
        set_language(lang)
        self.statusBar().showMessage(t("msg.ready"))
