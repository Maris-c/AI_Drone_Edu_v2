"""
MAVLinkPanel — Connection, Telemetry grid, and Command Log.

Layout:
  ┌─ 📡 MAVLink Connection ──────────────────── ● Connected ─┐
  │  [UDP ▼] [127.0.0.1] : [14550]       [ Connect ]         │
  ├── Telemetry ─────────────────────────────────────────────┤
  │  Mode  GUIDED   Battery  85%   Speed  1.2 m/s            │
  │  Alt   3.0 m    Lat      10.77 Lon    106.69             │
  │  Roll  -0.1°    Pitch    0.2°  Yaw    90.0°              │
  ├── COMMAND LOG ──────────────────── [Clear] ──────────────┤
  │  [12:34] → TAKEOFF alt=3m                                 │
  │  [12:34] ← ACK TAKEOFF: ✓ OK                             │
  └──────────────────────────────────────────────────────────┘
"""
from __future__ import annotations
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QTextEdit, QGridLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

import config


class MAVLinkPanel(QWidget):
    """Connection management + live telemetry display + command log."""

    connect_requested    = Signal(str)   # emits connection_string
    disconnect_requested = Signal()

    _MAX_LOG_LINES = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("mavCard")
        card.setStyleSheet(f"""
            QFrame#mavCard {{
                background: {config.COLOR_CARD};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        # ── Title row ─────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        icon_lbl = QLabel("📡")
        icon_lbl.setStyleSheet("font-size: 14px;")
        title_row.addWidget(icon_lbl)
        title_lbl = QLabel("MAVLink")
        title_lbl.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 13px; font-weight: 700;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color: {config.COLOR_MUTED}; font-size: 11px;")
        self._status_lbl = QLabel("Disconnected")
        self._status_lbl.setStyleSheet(
            f"color: {config.COLOR_MUTED}; font-size: 11px;"
        )
        title_row.addWidget(self._dot)
        title_row.addWidget(self._status_lbl)
        lay.addLayout(title_row)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {config.COLOR_BORDER}; border: none;")
        lay.addWidget(div)

        # ── Connection row ────────────────────────────────────────────────
        conn_row = QHBoxLayout()
        conn_row.setSpacing(5)

        self._proto = QComboBox()
        self._proto.addItems(["UDP", "TCP"])
        self._proto.setFixedWidth(60)
        self._proto.setFixedHeight(26)
        self._proto.setStyleSheet(self._combo_style())
        conn_row.addWidget(self._proto)

        self._host = QLineEdit("127.0.0.1")
        self._host.setFixedWidth(108)
        self._host.setFixedHeight(26)
        self._host.setStyleSheet(self._input_style())
        conn_row.addWidget(self._host)

        colon = QLabel(":")
        colon.setStyleSheet(f"color: {config.COLOR_MUTED};")
        conn_row.addWidget(colon)

        self._port = QLineEdit("14550")
        self._port.setFixedWidth(52)
        self._port.setFixedHeight(26)
        self._port.setStyleSheet(self._input_style())
        conn_row.addWidget(self._port)

        conn_row.addStretch()

        self._conn_btn = QPushButton("Connect")
        self._conn_btn.setFixedHeight(26)
        self._conn_btn.setFixedWidth(82)
        self._conn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._conn_btn.setStyleSheet(self._btn_style(config.COLOR_SUCCESS))
        self._conn_btn.clicked.connect(self._on_connect)
        conn_row.addWidget(self._conn_btn)

        lay.addLayout(conn_row)

        # ── Telemetry grid ────────────────────────────────────────────────
        telem = QFrame()
        telem.setStyleSheet(f"""
            QFrame {{
                background: {config.COLOR_BG};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        tgrid = QGridLayout(telem)
        tgrid.setContentsMargins(8, 6, 8, 6)
        tgrid.setHorizontalSpacing(10)
        tgrid.setVerticalSpacing(3)

        def _cell(label: str) -> tuple[QLabel, QLabel]:
            k = QLabel(label)
            k.setStyleSheet(f"color: {config.COLOR_MUTED}; font-size: 10px;")
            v = QLabel("—")
            v.setStyleSheet(
                f"color: {config.COLOR_TEXT}; font-size: 11px; font-weight: 600;"
            )
            return k, v

        kmode, self._t_mode   = _cell("Mode")
        kbat,  self._t_bat    = _cell("Battery")
        kspd,  self._t_speed  = _cell("Speed")
        kalt,  self._t_alt    = _cell("Alt")
        klat,  self._t_lat    = _cell("Lat")
        klon,  self._t_lon    = _cell("Lon")
        kroll, self._t_roll   = _cell("Roll")
        kpitch,self._t_pitch  = _cell("Pitch")
        kyaw,  self._t_yaw    = _cell("Yaw")

        cells = [
            (kmode, self._t_mode,  kbat,   self._t_bat,   kspd,  self._t_speed),
            (kalt,  self._t_alt,   klat,   self._t_lat,   klon,  self._t_lon),
            (kroll, self._t_roll,  kpitch, self._t_pitch, kyaw,  self._t_yaw),
        ]
        for row, (k1, v1, k2, v2, k3, v3) in enumerate(cells):
            tgrid.addWidget(k1, row, 0)
            tgrid.addWidget(v1, row, 1)
            tgrid.addWidget(k2, row, 2)
            tgrid.addWidget(v2, row, 3)
            tgrid.addWidget(k3, row, 4)
            tgrid.addWidget(v3, row, 5)

        lay.addWidget(telem)

        # ── Log header ────────────────────────────────────────────────────
        log_hdr = QHBoxLayout()
        log_title = QLabel("COMMAND LOG")
        log_title.setStyleSheet(
            f"color: {config.COLOR_MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        log_hdr.addWidget(log_title)
        log_hdr.addStretch()
        clr_btn = QPushButton("Clear")
        clr_btn.setFixedSize(40, 18)
        clr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clr_btn.setStyleSheet(
            f"font-size: 9px; color: {config.COLOR_MUTED}; background: transparent; "
            f"border: 1px solid {config.COLOR_BORDER}; border-radius: 4px;"
        )
        clr_btn.clicked.connect(self._log_widget.clear if hasattr(self, "_log_widget") else lambda: None)
        log_hdr.addWidget(clr_btn)
        lay.addLayout(log_hdr)

        # ── Log widget ────────────────────────────────────────────────────
        self._log_widget = QTextEdit()
        self._log_widget.setReadOnly(True)
        self._log_widget.setFixedHeight(88)
        self._log_widget.setStyleSheet(f"""
            QTextEdit {{
                background: {config.COLOR_BG};
                color: {config.COLOR_TEXT};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 6px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                padding: 3px 5px;
            }}
        """)
        lay.addWidget(self._log_widget)

        # Re-connect clear after _log_widget exists
        clr_btn.clicked.disconnect()
        clr_btn.clicked.connect(self._log_widget.clear)

        root.addWidget(card)

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_connect(self) -> None:
        if self._connected:
            self.disconnect_requested.emit()
        else:
            proto = self._proto.currentText().lower()
            host  = self._host.text().strip()
            port  = self._port.text().strip()
            conn  = f"{proto}:{host}:{port}"
            self._append(f"→ Connecting to {conn}…")
            self.connect_requested.emit(conn)

    # ── Public API ────────────────────────────────────────────────────────
    def update_connection(self, connected: bool, label: str) -> None:
        self._connected = connected
        color = config.COLOR_SUCCESS if connected else config.COLOR_MUTED
        self._dot.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._status_lbl.setText(label)
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        if connected:
            self._conn_btn.setText("Disconnect")
            self._conn_btn.setStyleSheet(self._btn_style(config.COLOR_DANGER))
        else:
            self._conn_btn.setText("Connect")
            self._conn_btn.setStyleSheet(self._btn_style(config.COLOR_SUCCESS))
        self._append(f"{'✓' if connected else '✗'} {label}")

    def update_telemetry(self, data: dict) -> None:
        self._t_mode.setText(str(data.get("mode", "—")))
        self._t_speed.setText(f"{data.get('speed', 0):.1f} m/s")
        self._t_alt.setText(f"{data.get('alt', 0):.1f} m")
        self._t_lat.setText(f"{data.get('lat', 0):.5f}°")
        self._t_lon.setText(f"{data.get('lon', 0):.5f}°")
        self._t_roll.setText(f"{data.get('roll', 0):.1f}°")
        self._t_pitch.setText(f"{data.get('pitch', 0):.1f}°")
        self._t_yaw.setText(f"{data.get('yaw', 0):.1f}°")

        # Battery with color coding
        bat = data.get("battery", -1)
        if isinstance(bat, int) and bat >= 0:
            self._t_bat.setText(f"{bat}%")
            c = (config.COLOR_SUCCESS if bat > 50
                 else config.COLOR_WARNING if bat > 20
                 else config.COLOR_DANGER)
            self._t_bat.setStyleSheet(
                f"color: {c}; font-size: 11px; font-weight: 600;"
            )

        # Mode color: green when armed
        armed = data.get("armed", False)
        mode_color = config.COLOR_SUCCESS if armed else config.COLOR_TEXT
        self._t_mode.setStyleSheet(
            f"color: {mode_color}; font-size: 11px; font-weight: 600;"
        )

    def append_log(self, msg: str) -> None:
        self._append(msg)

    # ── Log helpers ───────────────────────────────────────────────────────
    def _append(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        colored_msg = self._color_msg(msg)
        html = f'<span style="color:{config.COLOR_MUTED};">[{ts}]</span> {colored_msg}'
        self._log_widget.append(html)

        # Trim to max lines
        doc = self._log_widget.document()
        while doc.blockCount() > self._MAX_LOG_LINES:
            cursor = self._log_widget.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

        # Auto-scroll to bottom
        sb = self._log_widget.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _color_msg(self, msg: str) -> str:
        if msg.startswith(("→", "▶")):
            c = config.COLOR_ACCENT
        elif msg.startswith(("✓", "←")):
            c = config.COLOR_SUCCESS
        elif msg.startswith(("✗", "■")):
            c = config.COLOR_DANGER
        elif msg.startswith("⚠"):
            c = config.COLOR_WARNING
        elif msg.startswith("⏳"):
            c = config.COLOR_INFO
        else:
            c = config.COLOR_TEXT
        return f'<span style="color:{c};">{msg}</span>'

    # ── Style helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _btn_style(color: str) -> str:
        return f"""
            QPushButton {{
                background: {color}22;
                border: 1px solid {color}88;
                border-radius: 6px;
                color: {color};
                font-size: 11px;
                font-weight: 700;
                padding: 0 8px;
            }}
            QPushButton:hover {{ background: {color}44; border: 1px solid {color}; }}
            QPushButton:pressed {{ background: {color}66; }}
        """

    @staticmethod
    def _input_style() -> str:
        return f"""
            QLineEdit {{
                background: {config.COLOR_BG};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 5px;
                color: {config.COLOR_TEXT};
                font-size: 11px;
                padding: 1px 6px;
            }}
            QLineEdit:focus {{ border: 1px solid {config.COLOR_ACCENT}; }}
        """

    @staticmethod
    def _combo_style() -> str:
        return f"""
            QComboBox {{
                background: {config.COLOR_BG};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 5px;
                color: {config.COLOR_TEXT};
                font-size: 11px;
                padding: 1px 6px;
            }}
            QComboBox::drop-down {{ border: none; width: 14px; }}
            QComboBox QAbstractItemView {{
                background: {config.COLOR_CARD};
                color: {config.COLOR_TEXT};
                border: 1px solid {config.COLOR_BORDER};
                selection-background-color: {config.COLOR_ACCENT}44;
            }}
        """
