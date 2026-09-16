import os
import re
from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QRect,
    QRectF,
    QSize,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QScroller,
    QSplitter,
    QStackedLayout,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from joga_app.config import DATA_DIR, THUMBNAILS_DIR
from joga_app.i18n import t
from joga_app.ui.thumbnail_provider import ThumbnailProvider

# Rocket League rarity colors, used only as a quiet item-level cue.
QUALITY_COLORS = {
    "blackmarket": QColor("#e028b8"),
    "exotic": QColor("#f1c40f"),
    "import": QColor("#e74c3c"),
    "veryrare": QColor("#9b59b6"),
    "rare": QColor("#3498db"),
    "uncommon": QColor("#2ecc71"),
    "limited": QColor("#e67e22"),
    "premium": QColor("#d4af37"),
    "legacy": QColor("#00e5ff"),
    "common": QColor("#5a6b82"),
}
DEFAULT_QUALITY_COLOR = QColor("#3d495b")

CATEGORY_ICON_FILES = {
    "antenna": "category_Antennas.svg",
    "antennas": "category_Antennas.svg",
    "anthem": "category_Anthems.svg",
    "anthems": "category_Anthems.svg",
    "avatar border": "category_AvatarBorders.svg",
    "blueprint": "category_Items.svg",
    "body": "category_Bodies.png",
    "bodies": "category_Bodies.png",
    "boost": "category_Boosts.png",
    "rocket boost": "category_Boosts.png",
    "decal": "category_Decals.png",
    "flag": "category_Flags.svg",
    "engine audio": "category_EngineSounds.png",
    "engine sound": "category_EngineSounds.png",
    "goal explosion": "category_GoalExplosions.png",
    "misc": "category_Misc.svg",
    "paint finish": "category_PaintFinishes.png",
    "banner": "category_PlayerBanners.png",
    "player banner": "category_PlayerBanners.png",
    "topper": "category_Toppers.png",
    "trail": "category_Trails.png",
    "wheel": "category_Wheels.png",
    "wheels": "category_Wheels.png",
}


def _asset_key(value: str) -> str:
    """Normalize package and thumbnail names without touching catalog identity."""
    stem = os.path.splitext(os.path.basename(value or ""))[0]
    for suffix in ("_T_SF", "_SF"):
        if stem.upper().endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    return re.sub(r"[^a-z0-9]", "", stem.lower())


def get_rarity_color(quality_str: str) -> QColor:
    q = (quality_str or "").lower().replace(" ", "").replace("_", "")
    return QUALITY_COLORS.get(q, DEFAULT_QUALITY_COLOR)


class ItemCatalogModel(QAbstractListModel):
    """Backing data model for the virtual item catalog."""

    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.items = items or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.items)):
            return None
        item = self.items[index.row()]
        if role == Qt.DisplayRole:
            return item.label
        elif role == Qt.UserRole:
            return item
        elif role == Qt.ToolTipRole:
            return f"{item.label}\n{item.category} · {item.quality or 'Common'}\n{item.file}"
        return None

    def set_items(self, items):
        self.beginResetModel()
        self.items = items
        self.endResetModel()


class EquipmentMatrixDelegate(QStyledItemDelegate):
    """Renders restrained Rocket League inventory tiles."""

    def __init__(self, swaps_page, parent=None):
        super().__init__(parent)
        self.swaps_page = swaps_page
        self.slot_width = 204
        self.slot_height = 104
        self._pixmap_cache = {}
        self._item_thumbnails = {}
        if os.path.isdir(THUMBNAILS_DIR):
            for filename in os.listdir(THUMBNAILS_DIR):
                if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    self._item_thumbnails[_asset_key(filename)] = os.path.join(THUMBNAILS_DIR, filename)

    def _thumbnail_for(self, item):
        exact_path = self._item_thumbnails.get(_asset_key(item.file))
        if not exact_path:
            exact_path = self.swaps_page.thumbnail_provider.cached_path(item.file)
        if exact_path:
            path, exact = exact_path, True
        else:
            self.swaps_page.thumbnail_provider.request(item.file)
            filename = CATEGORY_ICON_FILES.get((item.category or "").strip().lower())
            path = os.path.join(DATA_DIR, filename) if filename else ""
            exact = False

        if not path or not os.path.isfile(path):
            return QPixmap(), False
        if path not in self._pixmap_cache:
            self._pixmap_cache[path] = QPixmap(path)
        return self._pixmap_cache[path], exact

    def sizeHint(self, option, index):
        return QSize(self.slot_width + 8, self.slot_height + 8)

    def paint(self, painter, option, index):
        item = index.data(Qt.UserRole)
        if not item:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect = option.rect.adjusted(3, 3, -3, -3)
        is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)

        # Check if item is currently assigned to Appearance or Owned Item
        is_appearance = (self.swaps_page._appearance_item and self.swaps_page._appearance_item.file == item.file)
        is_owned = (self.swaps_page._owned_item and self.swaps_page._owned_item.file == item.file)

        # Physical slot background and border
        if is_appearance:
            bg_color = QColor("#18191d")
            border_color = QColor("#d4af37")
            border_width = 1.5
        elif is_owned:
            bg_color = QColor("#18191d")
            border_color = QColor("#f2f0eb")
            border_width = 1.5
        elif is_hover:
            bg_color = QColor("#17181b")
            border_color = QColor("#3a3b40")
            border_width = 1.0
        else:
            bg_color = QColor("#111214")
            border_color = QColor("#292b30")
            border_width = 1.0

        # Draw equipment cell
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 2, 2)
        painter.fillPath(path, bg_color)
        painter.setPen(QPen(border_color, border_width))
        painter.drawPath(path)

        # Rarity is content metadata, not a decorative card gradient.
        rarity_color = get_rarity_color(item.quality)
        painter.setPen(QPen(rarity_color, 2))
        painter.drawLine(rect.x() + 2, rect.y() + 1, rect.right() - 2, rect.y() + 1)

        # Item artwork. Exact included thumbnails take priority; category art is
        # a deliberate low-contrast fallback for catalog entries with no image.
        artwork, is_exact_art = self._thumbnail_for(item)
        art_rect = QRect(rect.x() + 8, rect.y() + 11, 70, 70)
        if not artwork.isNull():
            scaled = artwork.scaled(
                art_rect.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            draw_x = art_rect.x() + (art_rect.width() - scaled.width()) // 2
            draw_y = art_rect.y() + (art_rect.height() - scaled.height()) // 2
            painter.setOpacity(1.0 if is_exact_art else 0.34)
            painter.drawPixmap(draw_x, draw_y, scaled)
            painter.setOpacity(1.0)
        else:
            painter.setPen(QPen(QColor("#3a3b40"), 1))
            painter.drawEllipse(art_rect.adjusted(12, 12, -12, -12))
            painter.setFont(QFont("Bahnschrift", 15, QFont.Bold))
            painter.setPen(QColor("#696a70"))
            painter.drawText(art_rect, Qt.AlignCenter, (item.category or "?")[:1].upper())

        # Item name
        name_font = QFont("Bahnschrift", 10, QFont.Bold)
        painter.setFont(name_font)
        painter.setPen(QColor("#f2f0eb" if (is_appearance or is_owned or is_hover) else "#d0cec8"))
        name_rect = QRect(rect.x() + 86, rect.y() + 12, rect.width() - 96, 43)
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, item.label)

        # Subtitle: Quality & Code
        sub_font = QFont("Segoe UI", 8)
        painter.setFont(sub_font)
        painter.setPen(QColor("#8f9096"))
        quality_tag = item.quality or "Common"
        sub_rect = QRect(rect.x() + 86, rect.bottom() - 38, rect.width() - 96, 30)
        detail_text = f"{item.category} · {quality_tag}"
        painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, detail_text)

        painter.restore()


class ItemFilterProxyModel(QSortFilterProxyModel):
    """Filters items by category and search query."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_text = ""
        self.category_filter = None

    def set_search(self, text):
        self.search_text = text.strip().lower()
        self.invalidateFilter()

    def set_category(self, cat):
        self.category_filter = cat
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        item = model.items[source_row]

        if self.category_filter:
            item_cat = (item.category or "").lower()
            filt_cat = self.category_filter.lower()
            if filt_cat not in item_cat and item_cat not in filt_cat:
                return False

        if self.search_text:
            s = self.search_text
            if (s not in item.label.lower() and
                s not in item.file.lower() and
                s not in (item.quality or "").lower()):
                return False

        return True


class SwapsPage(QWidget):
    """Purpose-built appearance → owned item workflow."""

    def __init__(self, cfg, catalog, backend):
        super().__init__()
        self.cfg = cfg
        self.catalog = catalog
        self.backend = backend
        self._install = None
        self._current_category = None
        self._all_items = []

        # Workflow state:
        # Slot 1: APPEARANCE (What cosmetic you want to see)
        # Slot 2: OWNED ITEM (What item you have equipped in garage)
        self._appearance_item = None
        self._owned_item = None
        self._active_focus = 1  # 1 = currently picking Appearance, 2 = picking Owned Item

        self.thumbnail_provider = ThumbnailProvider(self)

        self._build_ui()
        self.thumbnail_provider.thumbnail_ready.connect(self._on_thumbnail_ready)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # ==================================================================
        # 1. Core item swap workflow
        # ==================================================================
        self.bench_box = QFrame()
        self.bench_box.setObjectName("equipmentBench")
        bench_layout = QVBoxLayout(self.bench_box)
        bench_layout.setContentsMargins(18, 14, 18, 16)
        bench_layout.setSpacing(12)

        # Console Header Line
        bench_top_line = QHBoxLayout()
        bench_top_label = QLabel("ITEM SWAP")
        bench_top_label.setObjectName("sectionLabel")
        bench_top_line.addWidget(bench_top_label)
        bench_top_line.addStretch()

        self.revert_all_btn = QPushButton("RESTORE ALL")
        self.revert_all_btn.setObjectName("flatBtn")
        self.revert_all_btn.clicked.connect(self._on_restore_all)
        bench_top_line.addWidget(self.revert_all_btn)
        bench_layout.addLayout(bench_top_line)

        # Tactical Operation Rail (Appearance ──────► Owned Item ──► Apply)
        rail_layout = QHBoxLayout()
        rail_layout.setSpacing(12)

        # --- SLOT 01: APPEARANCE ---
        self.slot1_frame = QFrame()
        self.slot1_frame.setCursor(Qt.PointingHandCursor)
        self.slot1_frame.mousePressEvent = lambda e: self._set_focus(1)
        s1_lay = QVBoxLayout(self.slot1_frame)
        s1_lay.setContentsMargins(0, 0, 0, 0)
        s1_lay.setSpacing(3)

        s1_header = QHBoxLayout()
        self.s1_num = QLabel("01 APPEARANCE")
        self.s1_num.setObjectName("slotNumber")
        s1_header.addWidget(self.s1_num)
        s1_header.addStretch()
        self.s1_clear = QPushButton("CLEAR")
        self.s1_clear.setObjectName("flatBtn")
        self.s1_clear.clicked.connect(lambda: self._clear_slot(1))
        s1_header.addWidget(self.s1_clear)
        s1_lay.addLayout(s1_header)

        self.s1_ind = QLabel("How the item will look in-game")
        self.s1_ind.setObjectName("slotTargetIndicator")
        s1_lay.addWidget(self.s1_ind)

        self.s1_title = QLabel("Select an appearance")
        self.s1_title.setObjectName("slotNameEmpty")
        s1_lay.addWidget(self.s1_title)

        self.s1_meta = QLabel("Choose any compatible cosmetic from the items below")
        self.s1_meta.setObjectName("slotDetail")
        self.s1_meta.setWordWrap(True)
        s1_lay.addWidget(self.s1_meta)

        rail_layout.addWidget(self.slot1_frame, 4)

        # --- DIRECTION RAIL (Metallic Gold Vector) ---
        direction_box = QVBoxLayout()
        direction_box.setAlignment(Qt.AlignCenter)
        direction_box.setSpacing(4)
        rail_arrow = QLabel("──────────────────►")
        rail_arrow.setObjectName("directionRail")
        direction_box.addWidget(rail_arrow)
        swap_btn = QPushButton("⇄ REVERSE")
        swap_btn.setObjectName("flatBtn")
        swap_btn.setToolTip("Reverse swap direction")
        swap_btn.clicked.connect(self._swap_slot_assignment)
        direction_box.addWidget(swap_btn)
        rail_layout.addLayout(direction_box)

        # --- SLOT 02: OWNED ITEM ---
        self.slot2_frame = QFrame()
        self.slot2_frame.setCursor(Qt.PointingHandCursor)
        self.slot2_frame.mousePressEvent = lambda e: self._set_focus(2)
        s2_lay = QVBoxLayout(self.slot2_frame)
        s2_lay.setContentsMargins(0, 0, 0, 0)
        s2_lay.setSpacing(3)

        s2_header = QHBoxLayout()
        self.s2_num = QLabel("02 OWNED ITEM")
        self.s2_num.setObjectName("slotNumber")
        s2_header.addWidget(self.s2_num)
        s2_header.addStretch()
        self.s2_clear = QPushButton("CLEAR")
        self.s2_clear.setObjectName("flatBtn")
        self.s2_clear.clicked.connect(lambda: self._clear_slot(2))
        s2_header.addWidget(self.s2_clear)
        s2_lay.addLayout(s2_header)

        self.s2_ind = QLabel("The item currently owned in your garage")
        self.s2_ind.setObjectName("slotTargetIndicator")
        s2_lay.addWidget(self.s2_ind)

        self.s2_title = QLabel("Select an owned item")
        self.s2_title.setObjectName("slotNameEmpty")
        s2_lay.addWidget(self.s2_title)

        self.s2_meta = QLabel("Choose the matching item that will be replaced")
        self.s2_meta.setObjectName("slotDetail")
        self.s2_meta.setWordWrap(True)
        s2_lay.addWidget(self.s2_meta)

        rail_layout.addWidget(self.slot2_frame, 4)

        # --- ACTION BLOCK: Big Rectangular Brass Button ---
        action_box = QVBoxLayout()
        action_box.setAlignment(Qt.AlignCenter)
        action_box.setSpacing(6)

        self.apply_btn = QPushButton("APPLY SWAP")
        self.apply_btn.setObjectName("brassBtn")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply)
        action_box.addWidget(self.apply_btn)

        self.compat_status_lbl = QLabel("Choose both items")
        self.compat_status_lbl.setObjectName("statusTagNeutral")
        self.compat_status_lbl.setAlignment(Qt.AlignCenter)
        action_box.addWidget(self.compat_status_lbl)

        rail_layout.addLayout(action_box, 2)
        bench_layout.addLayout(rail_layout)

        main_layout.addWidget(self.bench_box)

        # ==================================================================
        # 2. EDITORIAL BROADCAST CATEGORY STRIP & SEARCH
        # ==================================================================
        cat_bar_layout = QHBoxLayout()
        cat_bar_layout.setSpacing(12)

        # Horizontal Category Strip in QScrollArea
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setFixedHeight(36)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        QScroller.grabGesture(
            cat_scroll.viewport(),
            QScroller.ScrollerGestureType.LeftMouseButtonGesture,
        )

        self.cat_strip_container = QWidget()
        self.cat_strip_layout = QHBoxLayout(self.cat_strip_container)
        self.cat_strip_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_strip_layout.setSpacing(12)
        self.cat_strip_layout.setAlignment(Qt.AlignLeft)
        cat_scroll.setWidget(self.cat_strip_container)
        cat_bar_layout.addWidget(cat_scroll, 1)

        # Search stays visually quiet so inventory remains the focus.
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items, files or rarity…")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setMaximumWidth(320)
        cat_bar_layout.addWidget(self.search_input)

        main_layout.addLayout(cat_bar_layout)

        # ==================================================================
        # 3. Item catalog and active swaps
        # ==================================================================
        splitter = QSplitter(Qt.Vertical)

        # --- TOP PANEL: EQUIPMENT INVENTORY MATRIX ---
        matrix_panel = QWidget()
        matrix_lay = QVBoxLayout(matrix_panel)
        matrix_lay.setContentsMargins(0, 0, 0, 0)
        matrix_lay.setSpacing(6)

        matrix_hdr = QHBoxLayout()
        matrix_title = QLabel("ITEMS")
        matrix_title.setObjectName("sectionLabel")
        matrix_hdr.addWidget(matrix_title)
        self.matrix_count_lbl = QLabel("")
        self.matrix_count_lbl.setObjectName("slotDetail")
        matrix_hdr.addWidget(self.matrix_count_lbl)
        matrix_hdr.addStretch()
        matrix_lay.addLayout(matrix_hdr)

        # Virtual QListView in IconMode (60 FPS virtualized matrix)
        self.matrix_view = QListView()
        self.matrix_view.setObjectName("equipmentMatrix")
        self.matrix_view.setViewMode(QListView.IconMode)
        self.matrix_view.setResizeMode(QListView.Adjust)
        self.matrix_view.setUniformItemSizes(True)
        self.matrix_view.setWordWrap(True)
        self.matrix_view.setSpacing(4)
        self.matrix_view.setMouseTracking(True)

        self.catalog_model = ItemCatalogModel()
        self.proxy_model = ItemFilterProxyModel()
        self.proxy_model.setSourceModel(self.catalog_model)
        self.matrix_view.setModel(self.proxy_model)

        self.matrix_delegate = EquipmentMatrixDelegate(self, self.matrix_view)
        self.matrix_view.setItemDelegate(self.matrix_delegate)
        self.matrix_view.clicked.connect(self._on_item_clicked)

        self.matrix_empty = QLabel("No items found\nCheck the selected installation or adjust your search.")
        self.matrix_empty.setObjectName("catalogEmpty")
        self.matrix_empty.setAlignment(Qt.AlignCenter)

        matrix_stage = QWidget()
        self.matrix_stack = QStackedLayout(matrix_stage)
        self.matrix_stack.setContentsMargins(0, 0, 0, 0)
        self.matrix_stack.addWidget(self.matrix_view)
        self.matrix_stack.addWidget(self.matrix_empty)
        matrix_lay.addWidget(matrix_stage, 1)
        splitter.addWidget(matrix_panel)

        # --- BOTTOM PANEL: ACTIVE SWAPS MATCH ROSTER ---
        roster_panel = QWidget()
        roster_lay = QVBoxLayout(roster_panel)
        roster_lay.setContentsMargins(0, 8, 0, 0)
        roster_lay.setSpacing(6)

        roster_hdr = QHBoxLayout()
        self.roster_title_lbl = QLabel("ACTIVE SWAPS")
        self.roster_title_lbl.setObjectName("sectionLabel")
        roster_hdr.addWidget(self.roster_title_lbl)
        roster_hdr.addStretch()
        roster_lay.addLayout(roster_hdr)

        # Scrollable squad sheet rows
        self.roster_scroll = QScrollArea()
        self.roster_scroll.setWidgetResizable(True)
        self.roster_scroll.setFrameShape(QFrame.NoFrame)
        self.roster_container = QWidget()
        self.roster_rows_layout = QVBoxLayout(self.roster_container)
        self.roster_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.roster_rows_layout.setSpacing(0)
        self.roster_rows_layout.addStretch()
        self.roster_scroll.setWidget(self.roster_container)
        roster_lay.addWidget(self.roster_scroll, 1)

        splitter.addWidget(roster_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, 1)

        self._update_focus_display()

    def _on_thumbnail_ready(self, _key):
        """Repaint visible inventory cells when an icon reaches our cache."""
        self.matrix_view.viewport().update()

    # ------------------------------------------------------------------
    # Public API called by MainWindow
    # ------------------------------------------------------------------

    def set_install(self, install):
        self._install = install
        self.refresh()

    def refresh(self):
        if not self._install:
            self.catalog_model.set_items([])
            return
        self._all_items = self.catalog.flat(self._install)
        self.catalog_model.set_items(self._all_items)
        self._build_category_strip()
        self._update_matrix_count()
        self._refresh_roster()

    # ------------------------------------------------------------------
    # Focus & Assignment Logic
    # ------------------------------------------------------------------

    def _set_focus(self, slot_num):
        self._active_focus = slot_num
        self._update_focus_display()

    def _update_focus_display(self):
        # Slot 1 visual focus indicator
        if self._active_focus == 1:
            self.s1_num.setStyleSheet("color: #d4af37; font-weight: 800;")
            self.s2_num.setStyleSheet("color: #8f9096; font-weight: 600;")
        else:
            self.s1_num.setStyleSheet("color: #8f9096; font-weight: 600;")
            self.s2_num.setStyleSheet("color: #d4af37; font-weight: 800;")

    def _clear_slot(self, slot_num):
        if slot_num == 1:
            self._appearance_item = None
            self.s1_title.setText("Select an appearance")
            self.s1_title.setObjectName("slotNameEmpty")
            self.s1_meta.setText("Choose any compatible cosmetic from the items below")
        else:
            self._owned_item = None
            self.s2_title.setText("Select an owned item")
            self.s2_title.setObjectName("slotNameEmpty")
            self.s2_meta.setText("Choose the matching item that will be replaced")

        self.s1_title.style().unpolish(self.s1_title)
        self.s1_title.style().polish(self.s1_title)
        self.s2_title.style().unpolish(self.s2_title)
        self.s2_title.style().polish(self.s2_title)
        self.matrix_view.viewport().update()
        self._validate_operation()

    def _swap_slot_assignment(self):
        self._appearance_item, self._owned_item = self._owned_item, self._appearance_item
        self._render_slot(1, self._appearance_item)
        self._render_slot(2, self._owned_item)
        self.matrix_view.viewport().update()
        self._validate_operation()

    def _render_slot(self, slot_num, item):
        title_lbl = self.s1_title if slot_num == 1 else self.s2_title
        meta_lbl = self.s1_meta if slot_num == 1 else self.s2_meta

        if item:
            title_lbl.setText(item.label)
            title_lbl.setObjectName("slotNameLocked")
            quality_tag = (item.quality or "COMMON").upper()
            meta_lbl.setText(f"{item.category} · {quality_tag.title()} · {item.file}")
        else:
            empty_text = "Select an appearance" if slot_num == 1 else "Select an owned item"
            title_lbl.setText(empty_text)
            title_lbl.setObjectName("slotNameEmpty")
            meta_lbl.setText("Choose an item below")

        title_lbl.style().unpolish(title_lbl)
        title_lbl.style().polish(title_lbl)

    def _on_item_clicked(self, proxy_index):
        if not proxy_index.isValid():
            return
        item = proxy_index.data(Qt.UserRole)
        if not item:
            return

        if self._active_focus == 1:
            self._appearance_item = item
            self._render_slot(1, item)
            # Flow forward: automatically switch focus to slot 2 if slot 2 is empty
            if self._owned_item is None:
                self._active_focus = 2
        else:
            self._owned_item = item
            self._render_slot(2, item)

        self._update_focus_display()
        self.matrix_view.viewport().update()
        self._validate_operation()

    def _validate_operation(self):
        src = self._owned_item
        tgt = self._appearance_item

        if src is None or tgt is None:
            self.compat_status_lbl.setText("Choose both items")
            self.compat_status_lbl.setObjectName("statusTagNeutral")
            self.apply_btn.setEnabled(False)
            self.compat_status_lbl.style().unpolish(self.compat_status_lbl)
            self.compat_status_lbl.style().polish(self.compat_status_lbl)
            return

        src_cat = (src.category or "").lower()
        tgt_cat = (tgt.category or "").lower()

        if src_cat == tgt_cat or ("wheel" in src_cat and "wheel" in tgt_cat) or ("boost" in src_cat and "boost" in tgt_cat):
            self.compat_status_lbl.setText(f"● Compatible · {src.category}")
            self.compat_status_lbl.setObjectName("statusTagOk")
            self.apply_btn.setEnabled(True)
        else:
            self.compat_status_lbl.setText(f"● Type mismatch · {src.category} / {tgt.category}")
            self.compat_status_lbl.setObjectName("statusTagWarn")
            self.apply_btn.setEnabled(True)

        self.compat_status_lbl.style().unpolish(self.compat_status_lbl)
        self.compat_status_lbl.style().polish(self.compat_status_lbl)

    # ------------------------------------------------------------------
    # Editorial Category Navigation Strip
    # ------------------------------------------------------------------

    def _build_category_strip(self):
        while self.cat_strip_layout.count():
            w = self.cat_strip_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        cat_counts = {}
        for it in self._all_items:
            cat_counts[it.category] = cat_counts.get(it.category, 0) + 1

        # ALL category button
        btn_all = QPushButton(f"ALL  {len(self._all_items)}")
        btn_all.setObjectName("categoryStripBtn")
        btn_all.setProperty("active", self._current_category is None)
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.clicked.connect(lambda: self._on_category_clicked(None))
        self.cat_strip_layout.addWidget(btn_all)

        # Individual categories
        for cat in sorted(cat_counts.keys()):
            count = cat_counts[cat]
            if count < 5:
                continue
            cat_upper = cat.upper()
            btn = QPushButton(f"{cat_upper}  {count}")
            btn.setObjectName("categoryStripBtn")
            btn.setProperty("active", self._current_category == cat)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, c=cat: self._on_category_clicked(c))
            self.cat_strip_layout.addWidget(btn)

    def _on_category_clicked(self, category):
        self._current_category = category
        self.proxy_model.set_category(category)
        self._update_matrix_count()
        for i in range(self.cat_strip_layout.count()):
            w = self.cat_strip_layout.itemAt(i).widget()
            if isinstance(w, QPushButton):
                is_active = (w.text().startswith("ALL ") and category is None) or (category and category.upper() in w.text())
                w.setProperty("active", is_active)
                w.style().unpolish(w)
                w.style().polish(w)

    def _on_search_changed(self, text):
        self.proxy_model.set_search(text)
        self._update_matrix_count()

    def _update_matrix_count(self):
        total = self.proxy_model.rowCount()
        self.matrix_count_lbl.setText(f"{total:,} available")
        self.matrix_stack.setCurrentWidget(self.matrix_view if total else self.matrix_empty)

    # ------------------------------------------------------------------
    # Actions: Apply, Restore, Restore All
    # ------------------------------------------------------------------

    def _status(self, msg):
        w = self.window()
        if w and hasattr(w, "statusBar"):
            w.statusBar().showMessage(msg, 6000)

    def _on_apply(self):
        install = self._install
        # Slot 1 is Appearance (target cosmetic), Slot 2 is Owned Item (source garage file)
        src = self._owned_item
        tgt = self._appearance_item
        if not install or not src or not tgt:
            return

        ok, msg_key, *args = self.backend.apply_swap(install, src, tgt)
        self._status(t(msg_key, *args))
        if not ok:
            QMessageBox.critical(self, t("msg.error"), t(msg_key, *args))
            return
        self._refresh_roster()

    def _on_restore(self, install, swap):
        ok, msg_key, *args = self.backend.restore_swap(install, swap)
        self._status(t(msg_key, *args))
        if not ok:
            QMessageBox.critical(self, t("msg.error"), t(msg_key, *args))
        self._refresh_roster()

    def _on_restore_all(self):
        install = self._install
        if not install:
            return
        reply = QMessageBox.question(
            self,
            t("msg.confirm"),
            t("msg.batch_restore_confirm", install.get("name", "")),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        count, errors = self.backend.restore_all(install)
        self._status(t("msg.batch_restored", count))
        self._refresh_roster()

    # ------------------------------------------------------------------
    # Match Squad Roster (Active Swaps)
    # ------------------------------------------------------------------

    def _refresh_roster(self):
        while self.roster_rows_layout.count() > 1:
            item = self.roster_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._install:
            return

        swaps = self.backend.presets.active_by_install(self._install.get("name", ""))
        self.roster_title_lbl.setText(f"ACTIVE SWAPS   {len(swaps)} active")

        if not swaps:
            empty_row = QWidget()
            empty_row.setObjectName("rosterRow")
            e_lay = QHBoxLayout(empty_row)
            e_lay.setContentsMargins(16, 12, 16, 12)
            e_lbl = QLabel("No active swaps. Choose an appearance and an owned item above to create one.")
            e_lbl.setObjectName("slotDetail")
            e_lay.addWidget(e_lbl)
            self.roster_rows_layout.insertWidget(0, empty_row)
            return

        for idx, swap in enumerate(swaps, start=1):
            row = QWidget()
            row.setObjectName("rosterRow")
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(12, 8, 12, 8)
            r_lay.setSpacing(16)

            # Roster index number
            idx_lbl = QLabel(f"{idx:02d}")
            idx_lbl.setObjectName("rosterIndex")
            idx_lbl.setFixedWidth(24)
            r_lay.addWidget(idx_lbl)

            # Source Item (Equipped item)
            src_lbl = QLabel(swap.source_label)
            src_lbl.setObjectName("rosterSource")
            r_lay.addWidget(src_lbl)

            arrow_lbl = QLabel("────────────►")
            arrow_lbl.setObjectName("rosterArrow")
            r_lay.addWidget(arrow_lbl)

            # Target Appearance (Wanted cosmetic)
            tgt_lbl = QLabel(swap.target_label)
            tgt_lbl.setObjectName("rosterTarget")
            r_lay.addWidget(tgt_lbl)

            r_lay.addSpacing(20)

            # Active In-Game pulse
            pulse_lbl = QLabel("● Active in-game")
            pulse_lbl.setObjectName("rosterActiveIndicator")
            r_lay.addWidget(pulse_lbl)

            r_lay.addStretch()

            # Platform Tag
            plat_lbl = QLabel(swap.install_name)
            plat_lbl.setObjectName("rosterPlatform")
            r_lay.addWidget(plat_lbl)

            # Revert action button
            revert_btn = QPushButton("RESTORE")
            revert_btn.setObjectName("revertBtn")
            revert_btn.clicked.connect(lambda _=False, s=swap, i=self._install: self._on_restore(i, s))
            r_lay.addWidget(revert_btn)

            self.roster_rows_layout.insertWidget(self.roster_rows_layout.count() - 1, row)
