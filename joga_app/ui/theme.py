"""Joga Bonito product stylesheet.

Aesthetics:
 - Calm specialist desktop software with a restrained football identity.
 - Neutral matte blacks, warm white text and deliberate metallic gold.
 - Sharp dividers, minimal containers and no neon or dashboard-card language.
 - Bahnschrift for branded display moments, Segoe UI for everyday interface copy.
"""

COLORS = {
    "bg_pitch": "#0a0a0b",
    "bg_console": "#111214",
    "bg_surface": "#16171b",
    "bg_surface_hover": "#1b1c20",
    "bg_surface_active": "#202126",
    "bg_input": "#0d0e10",
    "hairline": "#292b30",
    "hairline_light": "#3a3b40",
    "gold": "#d4af37",
    "gold_hover": "#e0bd4e",
    "gold_dim": "rgba(212, 175, 55, 0.12)",
    "text_bright": "#f2f0eb",
    "text_main": "#d0cec8",
    "text_muted": "#8f9096",
    "text_dark": "#0a0a0b",
    "green_active": "#2e7d4f",
    "red_alert": "#c1443c",
}

DARK_STYLESHEET = """
/* ===== Base Window & Application ===== */
QMainWindow {{
    background-color: {bg_pitch};
    color: {text_main};
    border: 1px solid {hairline};
}}
QWidget {{
    background-color: transparent;
    color: {text_main};
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}}

/* ===== Branded Window Chrome ===== */
#titleBar {{
    background-color: #080809;
    border-bottom: 1px solid {hairline};
}}
#titleBarTitle {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.4px;
    color: {text_bright};
}}
#titleBarContext {{
    font-size: 11px;
    color: #67686d;
}}
#windowControl, #windowClose {{
    background: transparent;
    border: none;
    border-radius: 0;
    color: {text_muted};
    min-width: 42px;
    max-width: 42px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    font-family: "Segoe UI", sans-serif;
    font-size: 15px;
}}
#windowControl:hover {{
    background-color: {bg_surface};
    color: {text_bright};
}}
#windowClose:hover {{
    background-color: {red_alert};
    color: #ffffff;
}}

/* ===== Stadium Wayfinding Sidebar ===== */
#sidebar {{
    background-color: {bg_pitch};
    border-right: 1px solid {hairline};
    min-width: 192px;
    max-width: 192px;
}}
#sidebarLogo {{
    padding-top: 0;
    padding-bottom: 6px;
}}
#sidebarTitle {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 2.4px;
    color: {text_bright};
    padding-bottom: 2px;
}}
#sidebarSubtitle {{
    font-family: "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 400;
    letter-spacing: 0;
    color: {text_muted};
    padding-bottom: 10px;
}}
#wayfindingBtn {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: {text_muted};
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 13px 17px;
    text-align: left;
    text-transform: uppercase;
}}
#wayfindingBtn:hover {{
    color: {text_bright};
    background-color: rgba(255, 255, 255, 0.02);
}}
#wayfindingBtn[active="true"] {{
    border-left: 3px solid {gold};
    color: {text_bright};
    font-weight: 700;
    background-color: transparent;
}}

/* ===== Platform Selector Frame ===== */
#platformBox {{
    border-top: 1px solid {hairline};
    padding-top: 14px;
    margin: 0 16px 16px 16px;
}}
#platformLabel {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: {text_muted};
    text-transform: uppercase;
    margin-bottom: 4px;
}}
#installCombo {{
    background-color: {bg_console};
    border: 1px solid {hairline};
    border-radius: 2px;
    color: {text_main};
    padding: 6px 10px;
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}}
#installCombo:hover {{
    border-color: {gold};
}}
#installCombo::drop-down {{
    border: none;
    width: 20px;
}}
#installCombo::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid {text_muted};
    margin-right: 6px;
}}
#installCombo QAbstractItemView {{
    background-color: {bg_console};
    border: 1px solid {hairline_light};
    color: {text_bright};
    selection-background-color: {gold};
    selection-color: {text_dark};
}}

/* ===== Content Area ===== */
#contentArea {{
    background-color: {bg_pitch};
}}

/* ===== Product Headers ===== */
#tacticalHeader {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 1.2px;
    color: {text_bright};
    text-transform: uppercase;
    padding: 0;
}}
#tacticalSub {{
    font-size: 11px;
    color: {text_muted};
    letter-spacing: 0;
}}
#sectionLabel {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.4px;
    color: {text_muted};
    text-transform: uppercase;
}}

/* ===== Buttons ===== */
QPushButton {{
    background-color: {bg_surface};
    border: 1px solid {hairline};
    border-radius: 2px;
    color: {text_main};
    padding: 8px 16px;
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
QPushButton:hover {{
    background-color: {bg_surface_hover};
    border-color: {hairline_light};
    color: {text_bright};
}}
QPushButton:pressed {{
    background-color: {bg_surface_active};
}}

/* Gold Brass CTA */
#brassBtn {{
    background-color: {gold};
    color: {text_dark};
    border: 1px solid {gold};
    border-radius: 2px;
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.8px;
    padding: 12px 28px;
    text-transform: uppercase;
}}
#brassBtn:hover {{
    background-color: {gold_hover};
    border-color: {gold_hover};
}}
#brassBtn:disabled {{
    background-color: #18191d;
    border-color: #202126;
    color: #5f6065;
}}

/* Clean Technical Outlines */
#flatBtn {{
    background: transparent;
    border: 1px solid {hairline};
    border-radius: 2px;
    color: {text_muted};
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    letter-spacing: 0.4px;
    padding: 5px 12px;
}}
#flatBtn:hover {{
    border-color: {gold};
    color: {gold};
}}

#revertBtn {{
    background: transparent;
    border: 1px solid rgba(248, 81, 73, 0.4);
    border-radius: 2px;
    color: {red_alert};
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 4px 10px;
    text-transform: uppercase;
}}
#revertBtn:hover {{
    background-color: rgba(248, 81, 73, 0.1);
    border-color: {red_alert};
}}

/* ===== Input Fields ===== */
QLineEdit {{
    background-color: {bg_input};
    border: 1px solid {hairline};
    border-radius: 2px;
    color: {text_bright};
    padding: 8px 12px;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
    selection-background-color: {gold};
    selection-color: {text_dark};
}}
QLineEdit:focus {{
    border-color: {gold};
}}

/* ===== Editorial Category Navigation Strip ===== */
#categoryStripBtn {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: {text_muted};
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1.5px;
    padding: 8px 14px;
    text-transform: uppercase;
}}
#categoryStripBtn:hover {{
    color: {text_bright};
}}
#categoryStripBtn[active="true"] {{
    border-bottom: 2px solid {gold};
    color: {text_bright};
    font-weight: 700;
}}

/* ===== Item Swap Workspace ===== */
#equipmentBench {{
    background-color: {bg_console};
    border: 1px solid {hairline};
    border-radius: 2px;
    padding: 16px 20px;
}}
#slotNumber {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.2px;
    color: {gold};
    text-transform: uppercase;
}}
#slotTargetIndicator {{
    font-family: "Segoe UI", sans-serif;
    font-size: 10px;
    color: {text_muted};
}}
#slotNameLocked {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 0.3px;
    color: {text_bright};
    text-transform: uppercase;
}}
#slotNameEmpty {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 1px;
    color: #696a70;
}}
#slotDetail {{
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
    color: {text_muted};
}}
#directionRail {{
    color: {gold};
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 2px;
}}
#statusTagOk {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.3px;
    color: {green_active};
}}
#statusTagWarn {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.3px;
    color: {red_alert};
}}
#statusTagNeutral {{
    font-family: "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: {text_muted};
}}

/* ===== Match Roster (Squad Sheet) ===== */
#rosterRow {{
    background-color: transparent;
    border-bottom: 1px solid {hairline};
    padding: 10px 4px;
}}
#rosterRow:hover {{
    background-color: rgba(255, 255, 255, 0.02);
}}
#rosterIndex {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 700;
    color: {gold};
    letter-spacing: 1px;
}}
#rosterSource {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: {text_bright};
}}
#rosterArrow {{
    color: {gold};
    font-size: 13px;
    font-weight: bold;
}}
#rosterTarget {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: {gold};
}}
#rosterPlatform {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {text_muted};
}}
#rosterActiveIndicator {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
    color: {green_active};
    text-transform: uppercase;
}}

/* ===== Equipment Matrix (QListView) ===== */
#equipmentMatrix {{
    background-color: {bg_pitch};
    border: none;
    border-top: 1px solid {hairline};
    outline: none;
    padding: 8px 0 0 0;
}}
#equipmentMatrix::item {{
    border: none;
    background: transparent;
}}
#catalogEmpty {{
    background-color: {bg_pitch};
    border-top: 1px solid {hairline};
    color: {text_muted};
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}
QSplitter::handle {{
    background-color: {hairline};
    height: 1px;
}}

/* ===== Technical 1px Scrollbars ===== */
QScrollBar:vertical {{
    background-color: {bg_pitch};
    width: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {hairline_light};
    min-height: 20px;
    border-radius: 0;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {gold};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: {bg_pitch};
    height: 5px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {hairline_light};
    min-width: 20px;
    border-radius: 0;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {gold};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QStatusBar {{
    background-color: #080809;
    border-top: 1px solid {hairline};
    color: {text_muted};
    font-size: 11px;
}}

/* ===== Technical Tables & Ledger ===== */
QTableWidget {{
    background-color: {bg_console};
    border: 1px solid {hairline};
    border-radius: 2px;
    gridline-color: transparent;
    outline: none;
    color: {text_main};
}}
QTableWidget::item {{
    border-bottom: 1px solid {hairline};
    padding: 8px 10px;
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}
QTableWidget::item:hover {{
    background-color: {bg_surface_hover};
    color: {text_bright};
}}
QTableWidget::item:selected {{
    background-color: {bg_surface_active};
    color: {text_bright};
}}
QHeaderView::section {{
    background-color: {bg_pitch};
    color: {text_muted};
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    border: none;
    border-bottom: 1px solid {hairline};
    padding: 10px 10px;
}}
QTableCornerButton::section {{
    background-color: {bg_pitch};
    border: none;
    border-bottom: 1px solid {hairline};
}}

/* ===== Technical Parameter Rows & Panels ===== */
#paramBox {{
    background-color: {bg_console};
    border: 1px solid {hairline};
    border-radius: 2px;
    padding: 14px 18px;
}}
#paramBox:hover {{
    border-color: {hairline_light};
}}
#paramLabel {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: {gold};
    text-transform: uppercase;
}}
#paramValue {{
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
    color: {text_main};
}}
#badgeConnected {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: {green_active};
    text-transform: uppercase;
}}
#badgeDisconnected {{
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: {red_alert};
    text-transform: uppercase;
}}
#manifestText {{
    font-family: "Consolas", "Segoe UI", monospace;
    font-size: 11px;
    color: {text_muted};
    line-height: 1.4;
}}

/* ===== Dialog Styling ===== */
QDialog {{
    background-color: {bg_pitch};
    color: {text_main};
    border: 1px solid {hairline_light};
}}
QDialog QLabel {{
    color: {text_main};
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}

/* ===== Tooltips ===== */
QToolTip {{
    background-color: {bg_console};
    color: {text_bright};
    border: 1px solid {hairline_light};
    border-radius: 2px;
    padding: 6px 10px;
    font-family: "Segoe UI", sans-serif;
    font-size: 12px;
}}
""".format(**COLORS)


def get_stylesheet(theme: str = "dark") -> str:
    return DARK_STYLESHEET
