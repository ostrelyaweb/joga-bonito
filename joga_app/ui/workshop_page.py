from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from joga_app.i18n import t
from joga_app.workshop.packages import WorkshopImportError


class WorkshopPage(QWidget):
    def __init__(self, cfg, service):
        super().__init__()
        self.cfg, self.service, self.install = cfg, service, None
        self.packages = []
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 24, 28, 24); layout.setSpacing(16)
        top = QHBoxLayout(); headings = QVBoxLayout()
        title = QLabel(t("workshop.title").upper()); title.setObjectName("tacticalHeader"); headings.addWidget(title)
        sub = QLabel(t("workshop.subtitle")); sub.setObjectName("tacticalSub"); headings.addWidget(sub)
        top.addLayout(headings); top.addStretch()
        button = QPushButton(t("workshop.import").upper()); button.setObjectName("primaryBtn"); button.clicked.connect(self._import); top.addWidget(button)
        layout.addLayout(top)
        body = QHBoxLayout(); body.setSpacing(16)
        left = QFrame(); left.setObjectName("equipmentBench"); ll = QVBoxLayout(left)
        self.list = QListWidget(); self.list.currentRowChanged.connect(self._selected_changed); ll.addWidget(self.list); body.addWidget(left, 2)
        right = QFrame(); right.setObjectName("equipmentBench"); rl = QVBoxLayout(right)
        self.name = QLabel(t("workshop.select")); self.name.setObjectName("slotName"); rl.addWidget(self.name)
        self.meta = QLabel(); self.meta.setObjectName("tacticalSub"); self.meta.setWordWrap(True); rl.addWidget(self.meta)
        self.output = QTextEdit(); self.output.setReadOnly(True); rl.addWidget(self.output, 1)
        actions = QHBoxLayout()
        self.preview_btn = QPushButton(t("workshop.preview").upper()); self.preview_btn.clicked.connect(self._preview); actions.addWidget(self.preview_btn)
        self.install_btn = QPushButton(t("workshop.install").upper()); self.install_btn.setObjectName("primaryBtn"); self.install_btn.clicked.connect(self._install); actions.addWidget(self.install_btn)
        self.restore_btn = QPushButton(t("workshop.restore").upper()); self.restore_btn.setObjectName("revertBtn"); self.restore_btn.clicked.connect(self._restore); actions.addWidget(self.restore_btn)
        self.remove_btn = QPushButton(t("workshop.remove").upper()); self.remove_btn.clicked.connect(self._remove); actions.addWidget(self.remove_btn)
        rl.addLayout(actions); body.addWidget(right, 3); layout.addLayout(body, 1)
        self.refresh()

    def set_install(self, install): self.install = install; self._selected_changed(self.list.currentRow())
    def _selected(self):
        row = self.list.currentRow(); return self.packages[row] if 0 <= row < len(self.packages) else None
    def refresh(self):
        selected = self._selected()[0].package_id if self._selected() else None
        self.packages = self.service.importer.list_packages(); self.list.clear(); active = {r.get("packageId") for r in self.service.installed(self.install.get("id") if self.install else None)}
        choice = 0
        for index, (manifest, _folder) in enumerate(self.packages):
            self.list.addItem(f"{'● ' if manifest.package_id in active else ''}{manifest.name}\n{manifest.category.upper()} · {manifest.author}")
            if manifest.package_id == selected: choice = index
        if self.packages: self.list.setCurrentRow(choice)
        else: self._selected_changed(-1)

    def _selected_changed(self, _row):
        item = self._selected()
        if not item:
            self.name.setText(t("workshop.select")); self.meta.clear(); self.output.clear(); return
        manifest, _folder = item; self.name.setText(manifest.name)
        self.meta.setText(f"{manifest.category.upper()} · {manifest.author}\n{len(manifest.files)} files\n{manifest.description}")
        active = bool(self.install and any(r.get("packageId") == manifest.package_id for r in self.service.installed(self.install.get("id"))))
        self.install_btn.setEnabled(bool(self.install) and not active); self.restore_btn.setEnabled(bool(self.install) and active); self.remove_btn.setEnabled(not any(r.get("packageId") == manifest.package_id for r in self.service.installed()))

    def _require(self):
        if not self.install: QMessageBox.warning(self, t("msg.warning"), t("msg.select_install")); return None
        return self._selected()
    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, t("workshop.import"), "", "Joga Workshop (*.jbworkshop)")
        if not path: return
        try: manifest, _folder = self.service.importer.import_package(path)
        except WorkshopImportError as exc: QMessageBox.critical(self, t("msg.error"), str(exc)); return
        self.refresh(); self._status(f"Imported: {manifest.name}")
    def _preview(self):
        item = self._require()
        if not item: return
        result = self.service.preview(item[0], item[1], self.install); self.output.setPlainText("\n".join((result.message, "", *result.actions)))
    def _install(self):
        item = self._require()
        if not item: return
        result = self.service.preview(item[0], item[1], self.install)
        if not result.compatible: QMessageBox.warning(self, t("msg.warning"), result.message); return
        if QMessageBox.question(self, t("msg.confirm"), "\n".join((result.message, "", *result.actions)), QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        ok, message = self.service.install(item[0], item[1], self.install); self._result(ok, message)
    def _restore(self):
        item = self._require()
        if not item: return
        ok, message = self.service.restore(item[0].package_id, self.install); self._result(ok, message)
    def _remove(self):
        item = self._selected()
        if not item: return
        ok, message = self.service.remove_imported(*item); self._result(ok, message)
    def _result(self, ok, message):
        (QMessageBox.information if ok else QMessageBox.critical)(self, t("msg.info") if ok else t("msg.error"), message); self._status(message); self.refresh()
    def _status(self, message):
        if hasattr(self.window(), "statusBar"): self.window().statusBar().showMessage(message, 7000)
