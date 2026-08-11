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
    QGraphicsOpacityEffect, QDoubleSpinBox,
)
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QPixmap, QLinearGradient,
    QDrag, QCursor
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve,
    QAbstractAnimation, QTimer, QSize, QMimeData
)

import config
from models.block import MissionBlock
from ui.mavlink_panel import MAVLinkPanel

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
    edit_requested = Signal(object)
    delete_requested = Signal(object)

    def __init__(self, block: MissionBlock, parent=None):
        super().__init__(parent)
        self.block = block
        self.setObjectName("missionBlockCard")
        self._build_ui()

    def _build_ui(self) -> None:
        c = self.block.color
        self.setStyleSheet(f"""
            QFrame#missionBlockCard {{
                background: {c};
                border: 1px solid {c};
                border-radius: 12px;
            }}
            QFrame#missionBlockCard:hover {{
                border: 1px solid #ffffff;
            }}
        """)

        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(10, 8, 10, 8)
        main_lay.setSpacing(10)

        # Icon and Title in a sub-frame
        info_frame = QFrame()
        info_lay = QHBoxLayout(info_frame)
        info_lay.setContentsMargins(8, 6, 12, 6)
        
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = _svg_pixmap(self.block.icon_name, 24)
        if pix:
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("🚁")
        info_lay.addWidget(icon_lbl)

        title = QLabel(self.block.title)
        title.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700;")
        info_lay.addWidget(title)
        main_lay.addWidget(info_frame)

        # Warning for TAKEOFF / LAND
        if self.block.cmd in ("TAKEOFF", "LAND"):
            warn_lbl = QLabel(f"⚠ {self.block.cmd}")
            warn_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 800; background: rgba(255,0,0,0.5); padding: 4px; border-radius: 4px;")
            main_lay.addWidget(warn_lbl)

        main_lay.addStretch()

        # Inline Edit
        self._param_edit = QDoubleSpinBox()
        self._param_edit.setDecimals(1)
        self._param_edit.setStyleSheet(f"""
            QDoubleSpinBox {{
                color: #FFFFFF; font-size: 11px; font-weight: 700;
                background: rgba(0,0,0,0.2); border-radius: 4px; padding: 2px 4px;
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; }}
        """)
        
        has_param = False
        if "alt" in self.block.params:
            self._param_edit.setRange(0.5, 10.0)
            self._param_edit.setValue(self.block.params["alt"])
            self._param_edit.setSuffix(" m")
            self._param_edit.valueChanged.connect(lambda v: self.edit_requested.emit((self, {"alt": v})))
            has_param = True
        elif "duration" in self.block.params:
            self._param_edit.setRange(0.5, 20.0)
            self._param_edit.setValue(self.block.params["duration"])
            self._param_edit.setSuffix(" s")
            self._param_edit.valueChanged.connect(lambda v: self.edit_requested.emit((self, {"duration": v})))
            has_param = True
        elif "delta" in self.block.params:
            self._param_edit.setRange(-10.0, 10.0)
            self._param_edit.setValue(self.block.params["delta"])
            self._param_edit.setSuffix(" m")
            self._param_edit.valueChanged.connect(lambda v: self.edit_requested.emit((self, {"delta": v})))
            has_param = True
        
        if self.block.cmd in ("TAKEOFF", "LAND") or not has_param:
            self._param_edit.hide()
            
        main_lay.addWidget(self._param_edit)

        # Actions
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(26, 26)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("background: rgba(255,0,0,0.4); color: white; border-radius: 13px; font-size: 12px;")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        main_lay.addWidget(del_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < 5:
            return

        drag = QDrag(self)
        mime = QMimeData()
        drag.setMimeData(mime)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.DropAction.MoveAction)

    def update_block(self, block: MissionBlock) -> None:
        self.block = block
        self._param_edit.blockSignals(True)
        if "alt" in block.params:
            self._param_edit.setValue(block.params["alt"])
        elif "duration" in block.params:
            self._param_edit.setValue(block.params["duration"])
        elif "delta" in block.params:
            self._param_edit.setValue(block.params["delta"])
        self._param_edit.blockSignals(False)


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
# Block Container for Drag and Drop
# ────────────────────────────────────────────────────────────────────────────
class BlockContainerWidget(QWidget):
    block_moved = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.source() and isinstance(event.source(), MissionBlockCard):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() and isinstance(event.source(), MissionBlockCard):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        source_card = event.source()
        if source_card and isinstance(source_card, MissionBlockCard):
            drop_y = event.position().y()
            lay = self.layout()
            
            cards = []
            for i in range(lay.count()):
                w = lay.itemAt(i).widget()
                if isinstance(w, MissionBlockCard):
                    cards.append(w)
            
            if source_card not in cards:
                event.ignore()
                return
                
            old_idx = cards.index(source_card)
            new_idx = len(cards)
            
            for i, card in enumerate(cards):
                if drop_y < card.y() + card.height() / 2:
                    new_idx = i
                    break
                    
            if new_idx > old_idx:
                new_idx -= 1
                
            if old_idx != new_idx:
                self.block_moved.emit(old_idx, new_idx)
                
            event.acceptProposedAction()
        else:
            event.ignore()


# ────────────────────────────────────────────────────────────────────────────
# Mission Panel
# ────────────────────────────────────────────────────────────────────────────
class MissionPanel(QWidget):
    run_requested    = Signal()
    stop_requested   = Signal()

    def __init__(self, mission_controller, mavlink_controller=None, parent=None):
        super().__init__(parent)
        self._mc                 = mission_controller
        self._mav_ctrl           = mavlink_controller
        self._block_cards:       List[MissionBlockCard] = []
        self._connector_widgets: List[ConnectorLine]    = []
        self._running            = False

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

        self._blocks_container = BlockContainerWidget()
        self._blocks_container.setStyleSheet("background: transparent;")
        self._blocks_container.block_moved.connect(self._mc.reorder_block)
        self._blocks_layout = QVBoxLayout(self._blocks_container)
        self._blocks_layout.setContentsMargins(0, 0, 0, 0)
        self._blocks_layout.setSpacing(0)
        self._blocks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Fixed Mission Start header
        self._blocks_layout.addWidget(MissionHeaderCard("Mission Start", config.COLOR_SUCCESS))
        self._blocks_layout.addStretch()

        self._scroll.setWidget(self._blocks_container)
        wrap_lay.addWidget(self._scroll)

        # ── MAVLink Panel ──────────────────────────────────────────────────
        self.mavlink_panel = MAVLinkPanel()
        if self._mav_ctrl:
            # Wire connection
            self.mavlink_panel.connect_requested.connect(self._mav_ctrl.connect_to)
            self.mavlink_panel.disconnect_requested.connect(self._mav_ctrl.disconnect)
            # Wire incoming signals
            self._mav_ctrl.connection_changed.connect(self.mavlink_panel.update_connection)
            self._mav_ctrl.telemetry_updated.connect(self.mavlink_panel.update_telemetry)
            self._mav_ctrl.command_ack.connect(self.mavlink_panel.append_log)
        wrap_lay.addWidget(self.mavlink_panel)

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

        # Connector
        if self._block_cards:
            conn = ConnectorLine()
            self._connector_widgets.append(conn)
            # Insert before stretch (last item)
            idx = self._blocks_layout.count() - 1
            self._blocks_layout.insertWidget(idx, conn)

        # Block card
        card = MissionBlockCard(block)
        card.edit_requested.connect(self._on_card_edited)
        card.delete_requested.connect(self._on_card_deleted)
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
    def _update_count(self) -> None:
        n = len(self._block_cards)
        self._block_count_lbl.setText(f"{n} block{'s' if n != 1 else ''}")

    def _scroll_to_bottom(self) -> None:
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_card_deleted(self, card: MissionBlockCard) -> None:
        if card in self._block_cards:
            idx = self._block_cards.index(card)
            self._mc.remove_block(idx)

    def _on_card_edited(self, data: tuple) -> None:
        card, new_params = data
        if card not in self._block_cards:
            return
        idx = self._block_cards.index(card)
        self._mc.update_block_params(idx, new_params)
