"""History of applied and restored cosmetic swaps."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from joga_app.i18n import t
from joga_app.swap_backend import SwapBackend


class HistoryPage(QWidget):
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
        title = QLabel(t("history.title").upper())
        title.setObjectName("tacticalHeader")
        header_box.addWidget(title)
        sub = QLabel("A chronological record of cosmetic changes")
        sub.setObjectName("tacticalSub")
        header_box.addWidget(sub)
        top.addLayout(header_box)
        top.addStretch()

        clear_btn = QPushButton(t("history.clear").upper())
        clear_btn.setObjectName("revertBtn")
        clear_btn.clicked.connect(self._on_clear)
        top.addWidget(clear_btn)
        layout.addLayout(top)

        # Audit Ledger Table Container
        self.table_container = QFrame()
        self.table_container.setObjectName("equipmentBench")
        tc_layout = QVBoxLayout(self.table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "#",
            t("history.source").upper(),
            "",
            t("history.target").upper(),
            t("history.install").upper(),
            t("history.time").upper(),
            t("history.actions").upper(),
        ])
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 48)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 36)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        tc_layout.addWidget(self.table)
        layout.addWidget(self.table_container, 1)

        # Empty State Bench
        self.empty_bench = QFrame()
        self.empty_bench.setObjectName("equipmentBench")
        eb_layout = QVBoxLayout(self.empty_bench)
        eb_layout.setContentsMargins(32, 48, 32, 48)
        eb_layout.setSpacing(8)
        eb_layout.setAlignment(Qt.AlignCenter)

        empty_title = QLabel("No history yet")
        empty_title.setObjectName("slotNameEmpty")
        empty_title.setAlignment(Qt.AlignCenter)
        eb_layout.addWidget(empty_title)

        empty_desc = QLabel(t("history.no_history"))
        empty_desc.setObjectName("tacticalSub")
        empty_desc.setAlignment(Qt.AlignCenter)
        eb_layout.addWidget(empty_desc)

        layout.addWidget(self.empty_bench)
        self.empty_bench.hide()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        history = list(reversed(SwapBackend.load_history()))

        if not history:
            self.table_container.hide()
            self.empty_bench.show()
            return

        self.empty_bench.hide()
        self.table_container.show()
        self.table.setRowCount(0)

        for i, entry in enumerate(history):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 44)

            # 0: Index (01, 02, etc.)
            idx_item = QTableWidgetItem(f"{i + 1:02d}")
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor("#d4af37"))
            self.table.setItem(row, 0, idx_item)

            # 1: Source (Desired Look)
            src_lbl = entry.get("sourceLabel", "") or "UNKNOWN"
            src_file = entry.get("sourceFile", "")
            src_text = f"{src_lbl}  [{src_file}]" if src_file else src_lbl
            src_item = QTableWidgetItem(src_text)
            src_item.setForeground(QColor("#f2f0eb"))
            self.table.setItem(row, 1, src_item)

            # 2: Directional vector
            arr_item = QTableWidgetItem("────►")
            arr_item.setTextAlignment(Qt.AlignCenter)
            arr_item.setForeground(QColor("#d4af37"))
            self.table.setItem(row, 2, arr_item)

            # 3: Target (Owned slot)
            tgt_lbl = entry.get("targetLabel", "") or "UNKNOWN"
            tgt_file = entry.get("targetFile", "")
            tgt_text = f"{tgt_lbl}  [{tgt_file}]" if tgt_file else tgt_lbl
            tgt_item = QTableWidgetItem(tgt_text)
            tgt_item.setForeground(QColor("#d4af37"))
            self.table.setItem(row, 3, tgt_item)

            # 4: Platform / Install
            inst_name = entry.get("installName", entry.get("installSource", "DEFAULT")).upper()
            inst_item = QTableWidgetItem(f"[{inst_name}]")
            inst_item.setTextAlignment(Qt.AlignCenter)
            inst_item.setForeground(QColor("#8f9096"))
            self.table.setItem(row, 4, inst_item)

            # 5: Timestamp
            time_str = entry.get("timestamp", "")
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignCenter)
            time_item.setForeground(QColor("#8f9096"))
            self.table.setItem(row, 5, time_item)

            # 6: Reapply button
            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(6, 4, 6, 4)
            h.setAlignment(Qt.AlignCenter)
            btn = QPushButton("REAPPLY")
            btn.setObjectName("flatBtn")
            btn.clicked.connect(lambda _=False, e=entry: self._on_reapply(e))
            h.addWidget(btn)
            self.table.setCellWidget(row, 6, cell)

    def _on_clear(self):
        reply = QMessageBox.question(
            self,
            t("msg.confirm"),
            t("history.clear_confirm"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            SwapBackend.clear_history()
            self.refresh()
            w = self.window()
            if w and hasattr(w, "statusBar"):
                w.statusBar().showMessage(t("msg.history_cleared"), 5000)

    def _on_reapply(self, entry_dict):
        ok, msg = self.backend.ensure_swap_applied(entry_dict)
        w = self.window()
        if w and hasattr(w, "statusBar"):
            w.statusBar().showMessage(msg, 5000)
        self.refresh()
