"""Transparent, draggable, non-injected overlay window."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class OverlayWindow(QWidget):
    moved = Signal(str, int, int)

    def __init__(self, overlay_id: str, title: str):
        super().__init__(None)
        self.overlay_id = overlay_id
        self.title = title
        self._drag_offset = QPoint()
        self._edit_mode = False
        self._click_through = True
        self._scale = 100
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(f"Joga Bonito — {title}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(3)
        self.title_label = QLabel(title.upper())
        self.value_label = QLabel("—")
        self.value_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self._apply_flags()
        self._apply_style()
        self.adjustSize()

    def configure(self, settings: dict, edit_mode: bool):
        self._scale = settings["scale"]
        self._edit_mode = edit_mode
        self._click_through = settings["clickThrough"]
        self._apply_flags()
        self.setWindowOpacity(settings["opacity"] / 100.0)
        self.move(settings["x"], settings["y"])
        self._apply_style()
        self.adjustSize()

    def _apply_flags(self):
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        if not self._edit_mode:
            flags |= Qt.WindowDoesNotAcceptFocus
            if self._click_through:
                flags |= Qt.WindowTransparentForInput
        visible = self.isVisible()
        self.setWindowFlags(flags)
        if visible:
            self.show()

    def _apply_style(self):
        title_size = max(8, round(9 * self._scale / 100))
        value_size = max(10, round(14 * self._scale / 100))
        border = "#ff5252" if self._edit_mode else "#d4af37"
        self.setStyleSheet(
            f"QWidget {{ background: rgba(13, 15, 18, 218); border: 1px solid {border}; "
            "border-radius: 5px; color: #f2f0eb; }}"
            f"QLabel {{ background: transparent; border: none; }}"
            f"QLabel:first {{ font-size: {title_size}px; }}"
        )
        self.title_label.setStyleSheet(
            f"color: {border}; font-size: {title_size}px; font-weight: 700; letter-spacing: 1px;"
        )
        self.value_label.setStyleSheet(
            f"color: #f2f0eb; font-size: {value_size}px; font-weight: 600;"
        )
        suffix = "  [EDIT]" if self._edit_mode else ""
        self.title_label.setText(self.title.upper() + suffix)

    def set_value(self, value: str):
        if self.value_label.text() != value:
            self.value_label.setText(value)
            self.adjustSize()

    def mousePressEvent(self, event):
        if self._edit_mode and event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._edit_mode and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._edit_mode and event.button() == Qt.LeftButton:
            self.moved.emit(self.overlay_id, self.x(), self.y())
            event.accept()
            return
        super().mouseReleaseEvent(event)
