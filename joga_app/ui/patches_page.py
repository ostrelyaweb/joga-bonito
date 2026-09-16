"""UI for validated redirect and paint patch packages."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from joga_app.i18n import t
from joga_app.patches import PackageImportError, PatchService


class PatchesPage(QWidget):
    def __init__(self, cfg, service: PatchService):
        super().__init__()
        self.cfg = cfg
        self.service = service
        self.install = None
        self._packages = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel(t("patches.title").upper())
        title.setObjectName("tacticalHeader")
        titles.addWidget(title)
        subtitle = QLabel(t("patches.subtitle"))
        subtitle.setObjectName("tacticalSub")
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        import_button = QPushButton(t("patches.import").upper())
        import_button.setObjectName("primaryBtn")
        import_button.clicked.connect(self._import_package)
        header.addWidget(import_button)
        layout.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)

        library = QFrame()
        library.setObjectName("equipmentBench")
        library_layout = QVBoxLayout(library)
        library_title = QLabel(t("patches.library").upper())
        library_title.setObjectName("sectionLabel")
        library_layout.addWidget(library_title)
        self.package_list = QListWidget()
        self.package_list.currentRowChanged.connect(self._show_selected)
        library_layout.addWidget(self.package_list, 1)
        content.addWidget(library, 2)

        detail = QFrame()
        detail.setObjectName("equipmentBench")
        detail_layout = QVBoxLayout(detail)
        self.name_label = QLabel(t("patches.select"))
        self.name_label.setObjectName("slotName")
        detail_layout.addWidget(self.name_label)
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("tacticalSub")
        self.meta_label.setWordWrap(True)
        detail_layout.addWidget(self.meta_label)
        self.preview_output = QTextEdit()
        self.preview_output.setReadOnly(True)
        self.preview_output.setPlaceholderText(t("patches.preview_hint"))
        detail_layout.addWidget(self.preview_output, 1)

        actions = QHBoxLayout()
        self.preview_button = QPushButton(t("patches.preview").upper())
        self.preview_button.setObjectName("flatBtn")
        self.preview_button.clicked.connect(self._preview)
        actions.addWidget(self.preview_button)
        self.apply_button = QPushButton(t("patches.apply").upper())
        self.apply_button.setObjectName("primaryBtn")
        self.apply_button.clicked.connect(self._apply)
        actions.addWidget(self.apply_button)
        self.restore_button = QPushButton(t("patches.restore").upper())
        self.restore_button.setObjectName("revertBtn")
        self.restore_button.clicked.connect(self._restore)
        actions.addWidget(self.restore_button)
        detail_layout.addLayout(actions)
        content.addWidget(detail, 3)
        layout.addLayout(content, 1)

    def set_install(self, install):
        self.install = install
        self._show_selected(self.package_list.currentRow())

    def refresh(self):
        selected_id = self._selected_manifest().patch_id if self._selected_manifest() else None
        self._packages = self.service.importer.list_manifests()
        self.package_list.blockSignals(True)
        self.package_list.clear()
        selected_row = -1
        active = {
            record.get("patchId")
            for record in self.service.active_records(
                self.install.get("id") if self.install else None
            )
        }
        for row, (manifest, _folder) in enumerate(self._packages):
            marker = "● " if manifest.patch_id in active else ""
            item = QListWidgetItem(f"{marker}{manifest.name}\n{manifest.kind.upper()} · {manifest.author}")
            item.setData(Qt.UserRole, manifest.patch_id)
            self.package_list.addItem(item)
            if manifest.patch_id == selected_id:
                selected_row = row
        self.package_list.blockSignals(False)
        if self._packages:
            self.package_list.setCurrentRow(selected_row if selected_row >= 0 else 0)
        else:
            self._show_selected(-1)

    def _selected_manifest(self):
        row = self.package_list.currentRow()
        if 0 <= row < len(self._packages):
            return self._packages[row][0]
        return None

    def _show_selected(self, _row):
        manifest = self._selected_manifest()
        if not manifest:
            self.name_label.setText(t("patches.select"))
            self.meta_label.clear()
            self.preview_output.clear()
            self.apply_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            return
        self.name_label.setText(manifest.name)
        self.meta_label.setText(
            f"{manifest.kind.upper()} · {manifest.author}\n"
            f"{manifest.target_file} · {len(manifest.operations)} {t('patches.operations')}\n"
            f"{manifest.description}"
        )
        active = bool(
            self.install
            and any(
                record.get("patchId") == manifest.patch_id
                for record in self.service.active_records(self.install.get("id"))
            )
        )
        self.apply_button.setEnabled(bool(self.install) and not active)
        self.restore_button.setEnabled(bool(self.install) and active)
        self.preview_output.setPlainText(t("patches.active") if active else t("patches.preview_hint"))

    def _import_package(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("patches.import"), "", "Joga Bonito Package (*.jbpkg)"
        )
        if not path:
            return
        try:
            manifest, _folder = self.service.importer.import_package(path)
        except PackageImportError as exc:
            QMessageBox.critical(self, t("msg.error"), str(exc))
            return
        self.refresh()
        for row, (candidate, _folder) in enumerate(self._packages):
            if candidate.patch_id == manifest.patch_id:
                self.package_list.setCurrentRow(row)
                break
        self._status(t("msg.patch_imported", manifest.name))

    def _require_selection(self):
        manifest = self._selected_manifest()
        if not self.install:
            QMessageBox.warning(self, t("msg.warning"), t("msg.select_install"))
            return None
        if not manifest:
            QMessageBox.warning(self, t("msg.warning"), t("patches.select"))
            return None
        return manifest

    def _preview(self):
        manifest = self._require_selection()
        if not manifest:
            return
        result = self.service.preview(manifest, self.install.get("cookedDir", ""))
        lines = [result.message, "", f"Target: {result.target}"]
        if result.changes:
            lines.extend(["", *result.changes])
        self.preview_output.setPlainText("\n".join(lines))
        self.apply_button.setEnabled(result.compatible)

    def _apply(self):
        manifest = self._require_selection()
        if not manifest:
            return
        preview = self.service.preview(manifest, self.install.get("cookedDir", ""))
        if not preview.compatible:
            self.preview_output.setPlainText(preview.message)
            QMessageBox.warning(self, t("msg.warning"), preview.message)
            return
        summary = "\n".join(preview.changes)
        answer = QMessageBox.question(
            self,
            t("msg.confirm"),
            t("patches.confirm_apply", manifest.name, summary),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        ok, message = self.service.apply(manifest, self.install)
        (QMessageBox.information if ok else QMessageBox.critical)(
            self, t("msg.info") if ok else t("msg.error"), message
        )
        self._status(message)
        self.refresh()

    def _restore(self):
        manifest = self._require_selection()
        if not manifest:
            return
        ok, message = self.service.restore(self.install, manifest.patch_id)
        (QMessageBox.information if ok else QMessageBox.critical)(
            self, t("msg.info") if ok else t("msg.error"), message
        )
        self._status(message)
        self.refresh()

    def _status(self, message):
        window = self.window()
        if window and hasattr(window, "statusBar"):
            window.statusBar().showMessage(message, 7000)
