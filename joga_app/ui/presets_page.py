from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QFileDialog, QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt

from joga_app.i18n import t


class PresetsPage(QWidget):
    def __init__(self, cfg, catalog, backend):
        super().__init__()
        self.cfg = cfg
        self.catalog = catalog
        self.backend = backend

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Page header
        top = QHBoxLayout()
        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        title = QLabel(t("presets.title").upper())
        title.setObjectName("tacticalHeader")
        header_box.addWidget(title)
        sub = QLabel("Save and switch between cosmetic configurations")
        sub.setObjectName("tacticalSub")
        header_box.addWidget(sub)
        top.addLayout(header_box)
        top.addStretch()

        new_btn = QPushButton("+  " + t("presets.new").upper())
        new_btn.setObjectName("brassBtn")
        new_btn.clicked.connect(self._on_new_preset)
        top.addWidget(new_btn)
        layout.addLayout(top)

        # Main bench
        bench = QFrame()
        bench.setObjectName("equipmentBench")
        b_lay = QHBoxLayout(bench)
        b_lay.setContentsMargins(16, 16, 16, 16)
        b_lay.setSpacing(18)

        self.preset_list = QListWidget()
        self.preset_list.setStyleSheet(
            "QListWidget { background-color: #0d0e10; border: 1px solid #292b30; outline: none; padding: 4px; }"
            "QListWidget::item { padding: 12px 14px; border-bottom: 1px solid #202126; font-family: 'Segoe UI', sans-serif; font-size: 13px; color: #d0cec8; }"
            "QListWidget::item:hover { background-color: #16171b; color: #f2f0eb; }"
            "QListWidget::item:selected { background-color: #18191d; border-left: 2px solid #d4af37; color: #f2f0eb; }"
        )
        self.preset_list.itemSelectionChanged.connect(self._on_selection_changed)
        b_lay.addWidget(self.preset_list, 1)

        actions = QVBoxLayout()
        actions.setSpacing(8)
        actions.setAlignment(Qt.AlignTop)

        self.apply_btn = QPushButton(t("presets.apply").upper())
        self.apply_btn.setObjectName("brassBtn")
        self.apply_btn.clicked.connect(self._on_apply_preset)
        actions.addWidget(self.apply_btn)

        self.delete_btn = QPushButton(t("presets.delete").upper())
        self.delete_btn.setObjectName("revertBtn")
        self.delete_btn.clicked.connect(self._on_delete_preset)
        actions.addWidget(self.delete_btn)

        self.import_btn = QPushButton(t("presets.import").upper())
        self.import_btn.setObjectName("flatBtn")
        self.import_btn.clicked.connect(self._on_import_preset)
        actions.addWidget(self.import_btn)

        self.export_btn = QPushButton(t("presets.export").upper())
        self.export_btn.setObjectName("flatBtn")
        self.export_btn.clicked.connect(self._on_export_preset)
        actions.addWidget(self.export_btn)

        b_lay.addLayout(actions)
        layout.addWidget(bench, 1)

        self.refresh()

    def refresh(self):
        self.preset_list.clear()
        current = self.backend.presets.current_preset
        for name in self.backend.presets.names():
            item = QListWidgetItem(name)
            p = next((x for x in self.backend.presets.presets if x.get("name") == name), None)
            count = len(p.get("swaps", [])) if p else 0
            badge = f"  ·  {count} swaps"
            if name == current:
                item.setText(f"{name}{badge}  ·  Active")
            else:
                item.setText(f"{name}{badge}")
            self.preset_list.addItem(item)
            if name == current:
                item.setSelected(True)
        self._on_selection_changed()

    def _selected_name(self):
        item = self.preset_list.currentItem()
        if not item:
            return None
        text = item.text()
        name = text.split("  ·  ")[0].strip()
        return name

    def _on_selection_changed(self):
        sel = self._selected_name()
        has_sel = sel is not None
        current = self.backend.presets.current_preset
        is_current = (sel and sel.upper() == current.upper())

        self.apply_btn.setEnabled(has_sel and not is_current)
        self.delete_btn.setEnabled(has_sel and not is_current and len(self.backend.presets.presets) > 1)
        self.export_btn.setEnabled(has_sel)

    def _status(self, msg):
        w = self.window()
        if w and hasattr(w, "statusBar"):
            w.statusBar().showMessage(msg, 5000)

    def _on_new_preset(self):
        name, ok = QInputDialog.getText(self, t("dlg.new_preset_title"), t("dlg.new_preset_prompt"))
        if not ok or not name.strip():
            return
        name = name.strip()
        self.backend.presets.save_as(name)
        self.refresh()
        self._status(t("msg.preset_created", name))

    def _on_apply_preset(self):
        name = self._selected_name()
        if not name:
            return
        self.backend.presets.switch(name)
        self.backend.check_for_drift()
        self.refresh()
        self._status(t("msg.preset_applied", name))

    def _on_delete_preset(self):
        name = self._selected_name()
        if not name:
            return
        reply = QMessageBox.question(
            self,
            t("msg.confirm"),
            t("msg.delete_preset_confirm", name),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if self.backend.presets.delete(name):
            self.refresh()
            self._status(t("msg.preset_deleted", name))

    def _on_import_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, t("presets.import"), "", "JSON (*.json)")
        if not path:
            return
        name = self.backend.presets.import_preset(path)
        if name:
            self.refresh()
            self._status(t("msg.preset_imported", name))
        else:
            QMessageBox.critical(self, t("msg.error"), t("msg.import_failed"))

    def _on_export_preset(self):
        name = self._selected_name()
        if not name:
            return
        path, _ = QFileDialog.getSaveFileName(self, t("presets.export"), f"{name}.json", "JSON (*.json)")
        if not path:
            return
        if self.backend.presets.export_preset(name, path):
            self._status(t("msg.preset_exported", path))
        else:
            QMessageBox.critical(self, t("msg.error"), t("msg.export_failed"))
