import os
from PySide6.QtWidgets import (
    QFrame, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtSvgWidgets import QSvgWidget


# ── Gesture → (Icon file, Display name, Block name) ──────────────────
GESTURE_DEFS = [
    ("Open Hand",   "takeoff.svg",  "Takeoff",    "Takeoff"),
    ("Fist",        "land.svg",     "Land",       "Land"),
    ("1 Finger",    "forward.svg",  "Forward",    "Forward"),
    ("2 Fingers",   "backward.svg", "Backward",   "Backward"),
    ("3 Fingers",   "right.svg",    "Move Right", "Move Right"),
    ("4 Fingers",   "left.svg",     "Move Left",  "Move Left"),
    ("Thumb Up",    "up.svg",       "Up",         "Up"),
    ("Thumb Down",  "down.svg",     "Down",       "Down"),
    ("Shaka",       "hover.svg",    "Hover",      "Hover"),
]

# Fallback emoji icons when SVG file is missing
EMOJI_FALLBACK = {
    "Open Hand":  "✋",
    "Fist":       "✊",
    "1 Finger":   "☝",
    "2 Fingers":  "✌",
    "3 Fingers":  "🤟",
    "4 Fingers":  "🖖",
    "Thumb Up":   "👍",
    "Thumb Down": "👎",
    "Shaka":      "🤙",
}

# Block type accent colors
GESTURE_COLORS = {
    "Takeoff":    "#8B5CF6",
    "Land":       "#8B5CF6",
    "Forward":    "#3B82F6",
    "Backward":   "#3B82F6",
    "Move Right": "#3B82F6",
    "Move Left":  "#3B82F6",
    "Up":         "#06B6D4",
    "Down":       "#06B6D4",
    "Hover":      "#F59E0B",
}


class GestureCard(QFrame):
    """Single gesture thumbnail card in the library grid."""
    clicked = Signal(str)   # Emits block_name

    def __init__(self, gesture_key: str, icon_file: str, display_name: str,
                 block_name: str, icons_dir: str, parent=None):
        super().__init__(parent)
        self.block_name = block_name
        accent = GESTURE_COLORS.get(block_name, "#8B5CF6")

        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {accent};
                background-color: rgba(139,92,246,0.06);
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Icon
        icon_path = os.path.join(icons_dir, icon_file)
        if os.path.exists(icon_path):
            try:
                svg = QSvgWidget(icon_path, self)
                svg.setFixedSize(36, 36)
                layout.addWidget(svg, 0, Qt.AlignHCenter)
            except Exception:
                self._add_emoji(layout, EMOJI_FALLBACK.get(gesture_key, "✋"))
        else:
            self._add_emoji(layout, EMOJI_FALLBACK.get(gesture_key, "✋"))

        # Gesture key (small, muted)
        lbl_key = QLabel(gesture_key, self)
        lbl_key.setAlignment(Qt.AlignCenter)
        lbl_key.setStyleSheet(
            "font-size: 9px; color: #64748B; background: transparent; font-weight: 500;"
        )
        layout.addWidget(lbl_key)

        # Block name (bold, accent)
        lbl_name = QLabel(display_name, self)
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {accent}; background: transparent;"
        )
        layout.addWidget(lbl_name)

    def _add_emoji(self, layout, emoji: str):
        lbl = QLabel(emoji, self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(lbl, 0, Qt.AlignHCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.block_name)
        super().mousePressEvent(event)


class GestureLibraryWidget(QFrame):
    """
    Displays the full gesture library as a 3-column card grid.
    Clicking a card emits gesture_selected for immediate block injection.
    """
    gesture_selected = Signal(str, float)   # block_name, duration

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        # Resolve icons directory (workspace root / icons)
        script_dir     = os.path.dirname(os.path.abspath(__file__))
        workspace_root = os.path.normpath(
            os.path.join(script_dir, "..", "..", "..", "..", "..")
        )
        self.icons_dir = os.path.join(workspace_root, "icons")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        lbl_section = QLabel("GESTURE LIBRARY", self)
        lbl_section.setObjectName("lbl-section")
        layout.addWidget(lbl_section)

        lbl_hint = QLabel("Click a card to insert a block instantly", self)
        lbl_hint.setStyleSheet(
            "font-size: 10px; color: #475569; background: transparent;"
        )
        layout.addWidget(lbl_hint)

        # 3-column grid
        grid = QGridLayout()
        grid.setSpacing(8)

        self._cards: dict[str, GestureCard] = {}

        for idx, (gkey, ifile, dname, bname) in enumerate(GESTURE_DEFS):
            card = GestureCard(gkey, ifile, dname, bname, self.icons_dir, self)
            card.clicked.connect(self._on_card_clicked)
            row = idx // 3
            col = idx % 3
            grid.addWidget(card, row, col)
            self._cards[bname] = card

        layout.addLayout(grid)

    def _on_card_clicked(self, block_name: str):
        self.gesture_selected.emit(block_name, 2.0)

    def get_mapped_action(self, gesture_name: str) -> str:
        """Returns block name for gesture name (for compatibility)."""
        # Direct match on block name
        if gesture_name in self._cards:
            return gesture_name
        # Search by gesture key mapping
        for gkey, _, _, bname in GESTURE_DEFS:
            if gkey == gesture_name or bname == gesture_name:
                return bname
        return gesture_name
