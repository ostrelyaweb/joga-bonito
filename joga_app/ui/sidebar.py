import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from joga_app.config import BASE_DIR
from joga_app.i18n import t


class Sidebar(QFrame):
    page_changed = Signal(int)
    install_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.installs = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Compact club identity block
        header_widget = QWidget()
        header_lay = QVBoxLayout(header_widget)
        header_lay.setContentsMargins(18, 20, 18, 18)
        header_lay.setSpacing(4)

        # Crest / Logo
        self.logo_label = QLabel()
        self.logo_label.setObjectName("sidebarLogo")
        icon_path = os.path.join(BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        self.logo_label.setAlignment(Qt.AlignLeft)
        header_lay.addWidget(self.logo_label)

        # Title
        self.title_label = QLabel("JOGA BONITO")
        self.title_label.setObjectName("sidebarTitle")
        header_lay.addWidget(self.title_label)

        # Subtitle
        self.sub_label = QLabel("Rocket League cosmetics")
        self.sub_label.setObjectName("sidebarSubtitle")
        header_lay.addWidget(self.sub_label)

        layout.addWidget(header_widget)

        # Wayfinding Navigation Links (Numbered stadium style)
        self.nav_buttons = []
        nav_entries = [
            ("01  " + t("nav.swaps"), 0),
            ("02  " + t("nav.presets"), 1),
            ("03  " + t("nav.history"), 2),
            ("04  " + t("nav.settings"), 3),
        ]

        for text, idx in nav_entries:
            btn = QPushButton(text)
            btn.setObjectName("wayfindingBtn")
            btn.setProperty("active", False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx: self._on_nav_clicked(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Game installation selector
        platform_box = QWidget()
        platform_box.setObjectName("platformBox")
        plat_lay = QVBoxLayout(platform_box)
        plat_lay.setContentsMargins(0, 0, 0, 0)
        plat_lay.setSpacing(4)

        plat_lbl = QLabel("GAME INSTALLATION")
        plat_lbl.setObjectName("platformLabel")
        plat_lay.addWidget(plat_lbl)

        self.install_combo = QComboBox()
        self.install_combo.setObjectName("installCombo")
        self.install_combo.currentIndexChanged.connect(self._on_install_changed)
        plat_lay.addWidget(self.install_combo)

        layout.addWidget(platform_box)

        self.set_active_page(0)

    def _on_nav_clicked(self, index):
        self.set_active_page(index)
        self.page_changed.emit(index)

    def _on_install_changed(self, index):
        if index >= 0 and self.installs:
            self.install_changed.emit()

    def set_installs(self, installs_list):
        self.installs = installs_list
        self.install_combo.blockSignals(True)
        self.install_combo.clear()
        for inst in self.installs:
            name = inst.get("name") or "?"
            self.install_combo.addItem(name, inst)
        self.install_combo.blockSignals(False)

        if self.installs:
            self.install_changed.emit()

    def current_install(self):
        idx = self.install_combo.currentIndex()
        if 0 <= idx < len(self.installs):
            return self.installs[idx]
        return None

    def set_active_page(self, index):
        for i, btn in enumerate(self.nav_buttons):
            is_active = (i == index)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
