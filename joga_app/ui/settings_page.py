"""Application, installation and catalog settings."""
import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QFileDialog, QComboBox, QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, Signal

from joga_app.i18n import t, available_languages
from joga_app.config import VERSION
from joga_app.update import UpdateClient
from joga_app.ui.update_worker import UpdateWorker


class SettingsPage(QWidget):
    theme_changed = Signal(str)
    language_changed = Signal(str)
    installs_changed = Signal()

    def __init__(self, cfg, catalog, backend):
        super().__init__()
        self.cfg = cfg
        self.catalog = catalog
        self.backend = backend
        self.update_client = UpdateClient()
        self.update_worker = None
        self.available_update = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        self.lay = QVBoxLayout(content)
        self.lay.setContentsMargins(28, 24, 28, 24)
        self.lay.setSpacing(16)
        scroll.setWidget(content)

        # Page header
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel(t("settings.title").upper())
        title.setObjectName("tacticalHeader")
        header_box.addWidget(title)
        sub = QLabel("Manage game installations, catalog data and preferences")
        sub.setObjectName("tacticalSub")
        header_box.addWidget(sub)
        self.lay.addLayout(header_box)

        self.lay.addSpacing(8)

        # ---- Section 1: Game Platform Directories ----
        self.lay.addWidget(self._section_label(t("settings.installs").upper()))

        self.installs_bench = QFrame()
        self.installs_bench.setObjectName("equipmentBench")
        self.installs_box = QVBoxLayout(self.installs_bench)
        self.installs_box.setContentsMargins(14, 14, 14, 14)
        self.installs_box.setSpacing(10)
        self.lay.addWidget(self.installs_bench)

        add_btn = QPushButton("+  " + t("settings.add").upper())
        add_btn.setObjectName("flatBtn")
        add_btn.clicked.connect(self._on_add_install)
        self.lay.addWidget(add_btn, alignment=Qt.AlignLeft)

        self.lay.addSpacing(12)

        # ---- Section 2: Items Database ----
        self.lay.addWidget(self._section_label(t("settings.items_db").upper()))

        db_bench = QFrame()
        db_bench.setObjectName("equipmentBench")
        db_lay = QVBoxLayout(db_bench)
        db_lay.setContentsMargins(16, 16, 16, 16)
        db_lay.setSpacing(10)

        db_input_row = QHBoxLayout()
        db_input_row.setSpacing(8)
        self.items_db_edit = QLineEdit(self.cfg.items_db)
        db_input_row.addWidget(self.items_db_edit, 1)

        browse = QPushButton(t("settings.browse").upper())
        browse.setObjectName("flatBtn")
        browse.clicked.connect(self._on_browse_items_db)
        db_input_row.addWidget(browse)

        save = QPushButton(t("settings.save").upper())
        save.setObjectName("brassBtn")
        save.clicked.connect(self._on_save_items_db)
        db_input_row.addWidget(save)
        db_lay.addLayout(db_input_row)

        self.items_count_label = QLabel()
        self.items_count_label.setObjectName("paramLabel")
        db_lay.addWidget(self.items_count_label)

        self.lay.addWidget(db_bench)

        self.lay.addSpacing(12)

        # ---- Section 3: Appearance & Language ----
        self.lay.addWidget(self._section_label(t("settings.appearance").upper() + " & LANGUAGE"))

        param_bench = QFrame()
        param_bench.setObjectName("equipmentBench")
        pb_lay = QVBoxLayout(param_bench)
        pb_lay.setContentsMargins(16, 16, 16, 16)
        pb_lay.setSpacing(14)

        # Theme
        theme_row = QHBoxLayout()
        t_lbl = QLabel(t("settings.theme").upper())
        t_lbl.setObjectName("paramLabel")
        t_lbl.setFixedWidth(160)
        theme_row.addWidget(t_lbl)

        self.theme_btns = {}
        for key in ("dark", "light", "auto"):
            btn = QPushButton(t(f"settings.theme_{key}").upper())
            btn.setObjectName("flatBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self._on_theme_changed(k))
            theme_row.addWidget(btn)
            self.theme_btns[key] = btn
        theme_row.addStretch()
        pb_lay.addLayout(theme_row)

        # Hairline separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #292b30; background-color: #292b30; height: 1px;")
        pb_lay.addWidget(sep)

        # Language
        lang_row = QHBoxLayout()
        l_lbl = QLabel(t("settings.language").upper())
        l_lbl.setObjectName("paramLabel")
        l_lbl.setFixedWidth(160)
        lang_row.addWidget(l_lbl)

        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("installCombo")
        for code, name in available_languages():
            self.lang_combo.addItem(name.upper(), code)
        idx = self.lang_combo.findData(self.cfg.language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        pb_lay.addLayout(lang_row)

        self.lay.addWidget(param_bench)

        self.lay.addSpacing(12)

        # ---- Section 4: Engine Manifest & Diagnostics ----
        self.lay.addWidget(self._section_label("ABOUT"))

        about_bench = QFrame()
        about_bench.setObjectName("equipmentBench")
        ab_lay = QVBoxLayout(about_bench)
        ab_lay.setContentsMargins(16, 16, 16, 16)
        ab_lay.setSpacing(6)

        m1 = QLabel(f"Joga Bonito Cosmetics v{VERSION}")
        m1.setObjectName("manifestText")
        m2 = QLabel("Package handling: Unreal Engine 3 · AES-256-ECB")
        m2.setObjectName("manifestText")
        m3 = QLabel("Catalog: Rocket League product definitions and package keys")
        m3.setObjectName("manifestText")
        m4 = QLabel("Compatible with Rocket League installations on Steam and Epic Games")
        m4.setObjectName("manifestText")

        ab_lay.addWidget(m1)
        ab_lay.addWidget(m2)
        ab_lay.addWidget(m3)
        ab_lay.addWidget(m4)

        update_row = QHBoxLayout()
        self.update_status = QLabel(t("settings.update_ready"))
        self.update_status.setObjectName("manifestText")
        update_row.addWidget(self.update_status, 1)
        self.update_btn = QPushButton(t("settings.check_updates").upper())
        self.update_btn.setObjectName("brassBtn")
        self.update_btn.clicked.connect(self._on_update_action)
        update_row.addWidget(self.update_btn)
        ab_lay.addLayout(update_row)
        self.lay.addWidget(about_bench)

        self.lay.addStretch()

    @staticmethod
    def _section_label(text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionLabel")
        return lbl

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        self._rebuild_installs()
        self._update_items_count()
        self._update_theme_pills()

    def _update_theme_pills(self):
        for key, btn in self.theme_btns.items():
            is_act = (key == self.cfg.theme)
            btn.setStyleSheet(
                "border-color: #d4af37; color: #f2f0eb; background-color: rgba(212, 175, 55, 0.08);"
                if is_act else ""
            )

    def _update_items_count(self):
        count = 0
        try:
            if os.path.isfile(self.cfg.items_db):
                with open(self.cfg.items_db, "r", encoding="utf-8") as f:
                    data = json.load(f)
                count = len(data) if isinstance(data, (list, dict)) else 0
        except Exception:
            pass
        self.items_count_label.setText(
            f"● {count:,} cosmetic items available"
        )

    # ------------------------------------------------------------------
    # Installs
    # ------------------------------------------------------------------

    def _rebuild_installs(self):
        while self.installs_box.count():
            w = self.installs_box.takeAt(0).widget()
            if w:
                w.deleteLater()

        for i, inst in enumerate(self.cfg.installs):
            row_frame = QFrame()
            row_frame.setObjectName("rosterRow")
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(6, 6, 6, 6)
            row.setSpacing(12)

            idx_lbl = QLabel(f"[{i + 1:02d}]")
            idx_lbl.setObjectName("rosterIndex")
            row.addWidget(idx_lbl)

            name_lbl = QLabel(inst.get("name", "?").upper())
            name_lbl.setObjectName("rosterSource")
            name_lbl.setFixedWidth(120)
            row.addWidget(name_lbl)

            cooked = inst.get("cookedDir", "")
            path_lbl = QLabel(cooked)
            path_lbl.setObjectName("paramValue")
            fm = path_lbl.fontMetrics()
            path_lbl.setText(fm.elidedText(cooked, Qt.ElideMiddle, 320))
            path_lbl.setToolTip(cooked)
            row.addWidget(path_lbl, 1)

            if os.path.isdir(cooked):
                badge = QLabel("● " + t("settings.connected").upper())
                badge.setObjectName("badgeConnected")
            else:
                badge = QLabel("○ " + t("settings.disconnected").upper())
                badge.setObjectName("badgeDisconnected")
            row.addWidget(badge)

            edit = QPushButton(t("settings.edit").upper())
            edit.setObjectName("flatBtn")
            edit.clicked.connect(lambda _=False, idx=i: self._on_edit_install(idx))
            row.addWidget(edit)

            rm = QPushButton(t("settings.remove").upper())
            rm.setObjectName("revertBtn")
            rm.clicked.connect(lambda _=False, idx=i: self._on_remove_install(idx))
            row.addWidget(rm)

            self.installs_box.addWidget(row_frame)

    def _on_add_install(self):
        from joga_app.ui.main_window import InstallDialog
        dlg = InstallDialog(self)
        if dlg.exec():
            vals = dlg.values()
            if not vals["name"] or not vals["cookedDir"]:
                QMessageBox.warning(self, t("msg.warning"), t("dlg.required"))
                return
            self.cfg.installs.append(vals)
            self.cfg.save()
            self.refresh()
            self.installs_changed.emit()

    def _on_edit_install(self, index):
        from joga_app.ui.main_window import InstallDialog
        if 0 <= index < len(self.cfg.installs):
            dlg = InstallDialog(self, self.cfg.installs[index])
            if dlg.exec():
                vals = dlg.values()
                if not vals["name"] or not vals["cookedDir"]:
                    QMessageBox.warning(self, t("msg.warning"), t("dlg.required"))
                    return
                self.cfg.installs[index] = vals
                self.cfg.save()
                self.refresh()
                self.installs_changed.emit()

    def _on_remove_install(self, index):
        if len(self.cfg.installs) <= 1:
            QMessageBox.warning(self, t("msg.warning"), t("msg.min_one_install"))
            return
        if 0 <= index < len(self.cfg.installs):
            self.cfg.installs.pop(index)
            self.cfg.save()
            self.refresh()
            self.installs_changed.emit()

    # ------------------------------------------------------------------
    # Items DB
    # ------------------------------------------------------------------

    def _on_browse_items_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("settings.browse"),
            os.path.dirname(self.items_db_edit.text()),
            "JSON (*.json)")
        if path:
            self.items_db_edit.setText(path)

    def _on_save_items_db(self):
        self.cfg.items_db = self.items_db_edit.text().strip()
        self.cfg.save()
        self.catalog._db = None  # force reload
        self._update_items_count()
        w = self.window()
        if w and hasattr(w, "statusBar"):
            w.statusBar().showMessage(t("msg.items_db_saved"), 5000)

    # ------------------------------------------------------------------
    # Theme & Language
    # ------------------------------------------------------------------

    def _on_theme_changed(self, theme):
        self.cfg.theme = theme
        self.cfg.save()
        self._update_theme_pills()
        self.theme_changed.emit(theme)

    def _on_language_changed(self, _index):
        code = self.lang_combo.currentData()
        if code and code != self.cfg.language:
            self.cfg.language = code
            self.cfg.save()
            self.language_changed.emit(code)

    def _on_update_action(self):
        mode = "download" if self.available_update else "check"
        self.update_btn.setEnabled(False)
        self.update_status.setText(t("settings.update_working"))
        self.update_worker = UpdateWorker(
            self.update_client, mode, self.available_update, self
        )
        self.update_worker.succeeded.connect(
            self._update_checked if mode == "check" else self._update_downloaded
        )
        self.update_worker.failed.connect(self._update_failed)
        self.update_worker.finished.connect(lambda: self.update_btn.setEnabled(True))
        self.update_worker.start()

    def _update_checked(self, manifest):
        if manifest.is_newer_than(VERSION):
            self.available_update = manifest
            self.update_status.setText(t("settings.update_available", manifest.version))
            self.update_btn.setText(t("settings.download_update").upper())
        else:
            self.update_status.setText(t("settings.update_current"))

    def _update_downloaded(self, path):
        self.update_status.setText(t("settings.update_verified", str(path)))
        if self.available_update.package_type == "installer":
            answer = QMessageBox.question(
                self, t("msg.confirm"), t("settings.launch_installer"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                try:
                    self.update_client.launch_installer(path)
                    QApplication.quit()
                except Exception as exc:
                    self._update_failed(str(exc))

    def _update_failed(self, message):
        self.update_status.setText(t("settings.update_failed", message))
        QMessageBox.warning(self, t("msg.warning"), message)
