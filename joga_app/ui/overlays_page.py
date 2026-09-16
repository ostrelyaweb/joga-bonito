"""Controls for independent external overlay windows."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from joga_app.i18n import t
from joga_app.overlays import OVERLAY_DEFINITIONS


class OverlaysPage(QWidget):
    def __init__(self, cfg, manager):
        super().__init__()
        self.cfg = cfg
        self.manager = manager
        self.controls = {}
        self._refreshing = False
        self._build_ui()
        self.manager.state_changed.connect(self.refresh)
        self.manager.game_running_changed.connect(self._game_state_changed)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel(t("overlays.title").upper())
        title.setObjectName("tacticalHeader")
        heading.addWidget(title)
        subtitle = QLabel(t("overlays.subtitle"))
        subtitle.setObjectName("tacticalSub")
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch()
        self.game_badge = QLabel()
        self.game_badge.setObjectName("statusBadge")
        header.addWidget(self.game_badge)
        layout.addLayout(header)

        notice = QFrame()
        notice.setObjectName("equipmentBench")
        notice_layout = QHBoxLayout(notice)
        note = QLabel(t("overlays.fullscreen_note"))
        note.setWordWrap(True)
        note.setObjectName("tacticalSub")
        notice_layout.addWidget(note)
        self.auto_show = QCheckBox(t("overlays.auto_show"))
        self.auto_show.toggled.connect(self._set_auto_show)
        notice_layout.addWidget(self.auto_show)
        layout.addWidget(notice)

        panel = QFrame()
        panel.setObjectName("equipmentBench")
        grid = QGridLayout(panel)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        for column, text in enumerate(
            (t("overlays.overlay"), t("overlays.enabled"), t("overlays.scale"),
             t("overlays.opacity"), t("overlays.click_through"))
        ):
            label = QLabel(text.upper())
            label.setObjectName("sectionLabel")
            grid.addWidget(label, 0, column)

        for row, (overlay_id, label_text) in enumerate(OVERLAY_DEFINITIONS, start=1):
            label = QLabel(t(f"overlays.{overlay_id}"))
            label.setObjectName("slotName")
            grid.addWidget(label, row, 0)

            enabled = QCheckBox()
            enabled.toggled.connect(
                lambda checked, key=overlay_id: self._set_enabled(key, checked)
            )
            grid.addWidget(enabled, row, 1, alignment=Qt.AlignCenter)

            scale = QSlider(Qt.Horizontal)
            scale.setRange(50, 200)
            scale.setSingleStep(5)
            scale.setToolTip("50% – 200%")
            scale.valueChanged.connect(
                lambda value, key=overlay_id: self._set_scale(key, value)
            )
            grid.addWidget(scale, row, 2)

            opacity = QSlider(Qt.Horizontal)
            opacity.setRange(20, 100)
            opacity.setSingleStep(5)
            opacity.setToolTip("20% – 100%")
            opacity.valueChanged.connect(
                lambda value, key=overlay_id: self._set_opacity(key, value)
            )
            grid.addWidget(opacity, row, 3)

            click_through = QCheckBox()
            click_through.toggled.connect(
                lambda checked, key=overlay_id: self._set_click_through(key, checked)
            )
            grid.addWidget(click_through, row, 4, alignment=Qt.AlignCenter)
            self.controls[overlay_id] = (enabled, scale, opacity, click_through)

        layout.addWidget(panel, 1)

        actions = QHBoxLayout()
        self.visibility_button = QPushButton()
        self.visibility_button.setObjectName("flatBtn")
        self.visibility_button.clicked.connect(self.manager.toggle_global)
        actions.addWidget(self.visibility_button)
        self.edit_button = QPushButton()
        self.edit_button.setObjectName("primaryBtn")
        self.edit_button.clicked.connect(self._toggle_edit)
        actions.addWidget(self.edit_button)
        reset_button = QPushButton(t("overlays.reset").upper())
        reset_button.setObjectName("revertBtn")
        reset_button.clicked.connect(self.manager.reset_positions)
        actions.addWidget(reset_button)
        actions.addStretch()
        self.hotkey_label = QLabel()
        self.hotkey_label.setObjectName("tacticalSub")
        actions.addWidget(self.hotkey_label)
        layout.addLayout(actions)

    def set_install(self, install):
        self.manager.set_install(install)

    def refresh(self):
        self._refreshing = True
        data = self.manager.store.data
        self.auto_show.setChecked(data["autoShowWithGame"])
        for overlay_id, controls in self.controls.items():
            settings = self.manager.store.overlay(overlay_id)
            controls[0].setChecked(settings["enabled"])
            controls[1].setValue(settings["scale"])
            controls[2].setValue(settings["opacity"])
            controls[3].setChecked(settings["clickThrough"])
        self.visibility_button.setText(
            (t("overlays.hide_all") if data["globalVisible"] else t("overlays.show_all")).upper()
        )
        self.edit_button.setText(
            (t("overlays.finish_edit") if data["editMode"] else t("overlays.edit_mode")).upper()
        )
        hotkey_status = t("overlays.hotkey_ok") if self.manager.hotkey.registered else t("overlays.hotkey_busy")
        self.hotkey_label.setText(hotkey_status)
        self._refreshing = False
        self._game_state_changed(self.manager.game_running)

    def _game_state_changed(self, running):
        self.game_badge.setText(
            t("overlays.game_running") if running else t("overlays.game_offline")
        )

    def _set_enabled(self, overlay_id, value):
        if not self._refreshing:
            self.manager.set_enabled(overlay_id, value)

    def _set_scale(self, overlay_id, value):
        if not self._refreshing:
            self.manager.set_scale(overlay_id, value)

    def _set_opacity(self, overlay_id, value):
        if not self._refreshing:
            self.manager.set_opacity(overlay_id, value)

    def _set_click_through(self, overlay_id, value):
        if not self._refreshing:
            self.manager.set_click_through(overlay_id, value)

    def _set_auto_show(self, value):
        if not self._refreshing:
            self.manager.set_auto_show(value)

    def _toggle_edit(self):
        self.manager.set_edit_mode(not self.manager.store.data["editMode"])
