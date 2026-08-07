"""
MissionPanel — Right panel (45 % width)

Sections:
  1. Header: "MISSION BUILDER" title + block count
  2. Warning banner (hidden by default)
  3. Scroll area: Mission Start header + block cards + connector lines
  4. Toolbar: Run / Stop / Clear / Export / Import
"""
from __future__ import annotations
import os
import json
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QFileDialog, QMessageBox,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve,
    QAbstractAnimation, QTimer, QSize,
)
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QPixmap, QLinearGradient,
)

import config
from models.block import MissionBlock

try:
    from PySide6.QtSvg import QSvgRenderer
    _SVG_OK = True
except ImportError:
    _SVG_OK = False


# ────────────────────────────────────────────────────────────────────────────
# Connector line between blocks
# ────────────────────────────────────────────────────────────────────────────
class ConnectorLine(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2

        pen = QPen(QColor(config.COLOR_BORDER), 2, Qt.PenStyle.SolidLine)
        p.setPen(pen)
        p.drawLine(cx, 0, cx, self.height() - 6)

        # Arrow head pointing down
        tip_y = self.height() - 4
        arr = 5
        p.drawLine(cx, tip_y, cx - arr, tip_y - arr)
        p.drawLine(cx, tip_y, cx + arr, tip_y - arr)
        p.end()


# ────────────────────────────────────────────────────────────────────────────
# Mission Start / Mission End header card (static)
# ────────────────────────────────────────────────────────────────────────────
class MissionHeaderCard(QFrame):
    def __init__(self, label: str = "Mission Start", color: str = config.COLOR_SUCCESS, parent=None):
        super().__init__(parent)
        self.setObjectName("missionHeaderCard")
        self.setFixedHeight(46)
        self.setStyleSheet(f"""
            QFrame#missionHeaderCard {{
                background: {color}18;
                border: 1px solid {color}55;
                border-left: 3px solid {color};
                border-radius: 10px;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)

        icon = QLabel("▶")
        icon.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700;")
        lay.addWidget(icon)

        lbl = QLabel(f"[ {label} ]")
        lbl.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 13px; font-weight: 700; font-family: 'Courier New';"
        )
        lay.addWidget(lbl)
        lay.addStretch()


# ────────────────────────────────────────────────────────────────────────────
# Mission Block Card
# ────────────────────────────────────────────────────────────────────────────
def _svg_pixmap(icon_name: str, size: int = 30) -> QPixmap | None:
    path = os.path.join(config.ICONS_DIR, f"{icon_name}.svg")
    if not _SVG_OK or not os.path.exists(path):
        return None
    r = QSvgRenderer(path)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    pp = QPainter(pix)
    r.render(pp)
    pp.end()
    return pix


class MissionBlockCard(QFrame):
    def __init__(self, block: MissionBlock, parent=None):
        super().__init__(parent)
        self.block = block
        self.setObjectName("missionBlockCard")
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"""
            QFrame#missionBlockCard {{
                background: {config.COLOR_CARD};
                border: 1px solid {config.COLOR_BORDER};
                border-left: 4px solid {self.block.color};
                border-radius: 12px;
            }}
            QFrame#missionBlockCard:hover {{
                border: 1px solid {self.block.color}88;
                border-left: 4px solid {self.block.color};
                background: #1f2f47;
            }}
        """)

        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(14, 10, 14, 10)
        main_lay.setSpacing(12)

        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = _svg_pixmap(self.block.icon_name, 32)
        if pix:
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("🚁")
            icon_lbl.setStyleSheet("font-size: 20px;")
        main_lay.addWidget(icon_lbl)

        # Text area
        text_lay = QVBoxLayout()
        text_lay.setSpacing(3)

        # Tag label  [GESTURE] or [MISSION START]
        tag = QLabel(f"[ {self.block.get_tag()} ]")
        tag.setStyleSheet(
            f"color: {config.COLOR_MUTED}; font-size: 10px; font-family: 'Courier New';"
        )
        text_lay.addWidget(tag)

        # Title
        title = QLabel(self.block.title)
        title.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 14px; font-weight: 700;"
        )
        text_lay.addWidget(title)

        main_lay.addLayout(text_lay)
        main_lay.addStretch()

        # Param chip
        self._param_lbl = QLabel(self.block.get_param_text())
        self._param_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._param_lbl.setStyleSheet(
            f"color: {self.block.color}; font-size: 12px; font-weight: 600; "
            f"background: {self.block.color}18; border-radius: 6px; padding: 3px 8px;"
        )
        self._param_lbl.setMinimumWidth(80)
        main_lay.addWidget(self._param_lbl)

    def update_block(self, block: MissionBlock) -> None:
        self.block = block
        self._param_lbl.setText(block.get_param_text())


# ────────────────────────────────────────────────────────────────────────────
# Warning banner
# ────────────────────────────────────────────────────────────────────────────
class WarningBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("warningBanner")
        self.setStyleSheet(f"""
            QFrame#warningBanner {{
                background: {config.COLOR_WARNING}22;
                border: 1px solid {config.COLOR_WARNING}88;
                border-radius: 8px;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        self._lbl = QLabel()
        self._lbl.setStyleSheet(f"color: {config.COLOR_WARNING}; font-size: 12px; font-weight: 600;")
        self._lbl.setWordWrap(True)
        lay.addWidget(self._lbl)
        self.hide()

    def show_message(self, msg: str) -> None:
        self._lbl.setText(msg)
        self.show()

    def hide_message(self) -> None:
        self.hide()


# ────────────────────────────────────────────────────────────────────────────
# Mission Panel
# ────────────────────────────────────────────────────────────────────────────
class MissionPanel(QWidget):
    run_requested    = Signal()
    stop_requested   = Signal()

    def __init__(self, mission_controller, parent=None):
        super().__init__(parent)
        self._mc              = mission_controller
        self._block_cards:    List[MissionBlockCard] = []
        self._connector_widgets: List[ConnectorLine]  = []
        self._running         = False

        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Outer padding
        wrap = QWidget()
        wrap_lay = QVBoxLayout(wrap)
        wrap_lay.setContentsMargins(16, 16, 16, 16)
        wrap_lay.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        title_bar = QLabel()
        title_bar.setFixedSize(3, 22)
        title_bar.setStyleSheet(f"background: {config.COLOR_ACCENT}; border-radius: 2px;")
        title_row.addWidget(title_bar)

        title_lbl = QLabel("MISSION BUILDER")
        title_lbl.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 16px; font-weight: 700;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self._block_count_lbl = QLabel("0 blocks")
        self._block_count_lbl.setStyleSheet(
            f"color: {config.COLOR_MUTED}; font-size: 11px;"
        )
        title_row.addWidget(self._block_count_lbl)
        wrap_lay.addLayout(title_row)

        # Warning banner
        self._warning = WarningBanner()
        wrap_lay.addWidget(self._warning)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical {
                background: #1a2236;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self._blocks_container = QWidget()
        self._blocks_container.setStyleSheet("background: transparent;")
        self._blocks_layout = QVBoxLayout(self._blocks_container)
        self._blocks_layout.setContentsMargins(0, 0, 0, 0)
        self._blocks_layout.setSpacing(0)
        self._blocks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Fixed Mission Start header
        self._blocks_layout.addWidget(MissionHeaderCard("Mission Start", config.COLOR_SUCCESS))
        self._blocks_layout.addStretch()

        self._scroll.setWidget(self._blocks_container)
        wrap_lay.addWidget(self._scroll)

        # Empty state label
        self._empty_lbl = QLabel("✨ Gesture detected blocks\nwill appear here automatically")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color: {config.COLOR_MUTED}; font-size: 12px; line-height: 1.6;"
        )
        self._blocks_layout.insertWidget(1, self._empty_lbl)  # Between header and stretch

        # Toolbar
        wrap_lay.addWidget(self._build_toolbar())

        root.addWidget(wrap)

    def _build_toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("toolbar")
        bar.setFixedHeight(54)
        bar.setStyleSheet(f"""
            QFrame#toolbar {{
                background: {config.COLOR_CARD};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 12px;
            }}
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        self._run_btn = self._tool_btn("▶  Run",   config.COLOR_SUCCESS)
        self._stp_btn = self._tool_btn("■  Stop",  config.COLOR_DANGER)
        clr_btn       = self._tool_btn("✕  Clear", config.COLOR_MUTED)
        exp_btn       = self._tool_btn("↑  Export", config.COLOR_INFO)
        imp_btn       = self._tool_btn("↓  Import", config.COLOR_INFO)

        self._run_btn.clicked.connect(self._on_run)
        self._stp_btn.clicked.connect(self._on_stop)
        clr_btn.clicked.connect(self._on_clear)
        exp_btn.clicked.connect(self._on_export)
        imp_btn.clicked.connect(self._on_import)

        for btn in (self._run_btn, self._stp_btn, clr_btn, exp_btn, imp_btn):
            lay.addWidget(btn)

        return bar

    @staticmethod
    def _tool_btn(text: str, color: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}22;
                border: 1px solid {color}66;
                border-radius: 8px;
                color: {color};
                font-size: 11px;
                font-weight: 700;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background: {color}44;
                border: 1px solid {color};
            }}
            QPushButton:pressed {{
                background: {color}66;
            }}
        """)
        return btn

    # ── Slots from MissionController ─────────────────────────────────────
    def add_block(self, block: MissionBlock) -> None:
        self._hide_empty()

        # Connector
        if self._block_cards:
            conn = ConnectorLine()
            self._connector_widgets.append(conn)
            # Insert before stretch (last item)
            idx = self._blocks_layout.count() - 1
            self._blocks_layout.insertWidget(idx, conn)

        # Block card
        card = MissionBlockCard(block)
        card.setMaximumHeight(0)
        idx = self._blocks_layout.count() - 1
        self._blocks_layout.insertWidget(idx, card)
        self._block_cards.append(card)

        # Animate expand
        target_h = 72
        anim = QPropertyAnimation(card, b"maximumHeight", card)
        anim.setDuration(280)
        anim.setStartValue(0)
        anim.setEndValue(target_h)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

        # Animate opacity
        fx = QGraphicsOpacityEffect(card)
        card.setGraphicsEffect(fx)
        oa = QPropertyAnimation(fx, b"opacity", card)
        oa.setDuration(280)
        oa.setStartValue(0.0)
        oa.setEndValue(1.0)
        oa.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

        self._update_count()
        QTimer.singleShot(320, self._scroll_to_bottom)

    def update_block(self, idx: int, block: MissionBlock) -> None:
        if 0 <= idx < len(self._block_cards):
            self._block_cards[idx].update_block(block)

    def clear_blocks(self) -> None:
        for w in self._block_cards + self._connector_widgets:
            w.setParent(None)
            w.deleteLater()
        self._block_cards.clear()
        self._connector_widgets.clear()
        self._update_count()
        self._show_empty()

    def load_blocks(self, blocks: list) -> None:
        self.clear_blocks()
        for b in blocks:
            self.add_block(b)

    def show_warning(self, msg: str) -> None:
        self._warning.show_message(msg)
        QTimer.singleShot(4000, self._warning.hide_message)

    def clear_warning(self) -> None:
        self._warning.hide_message()

    # ── Toolbar slots ────────────────────────────────────────────────────
    def _on_run(self) -> None:
        blocks = self._mc.blocks()
        if not blocks:
            self.show_warning("⚠  Mission is empty — add gesture blocks first.")
            return
        self._running = True
        self.run_requested.emit()

    def _on_stop(self) -> None:
        self._running = False
        self.stop_requested.emit()

    def _on_clear(self) -> None:
        self._mc.clear()

    def _on_export(self) -> None:
        if not self._mc.blocks():
            self.show_warning("⚠  Nothing to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Mission JSON", "mission.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._mc.export_json())

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Mission JSON", "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            ok, msg = self._mc.import_json(text)
            if not ok:
                self.show_warning(f"✗ Import failed: {msg}")

    # ── Helpers ──────────────────────────────────────────────────────────
    def _hide_empty(self) -> None:
        self._empty_lbl.hide()

    def _show_empty(self) -> None:
        self._empty_lbl.show()

    def _update_count(self) -> None:
        n = len(self._block_cards)
        self._block_count_lbl.setText(f"{n} block{'s' if n != 1 else ''}")

    def _scroll_to_bottom(self) -> None:
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
