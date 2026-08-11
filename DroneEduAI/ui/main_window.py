"""
MainWindow — QMainWindow shell.

Layers (top → bottom):
  ┌───────────────────────────── header bar ──────────────────────────────┐
  │  🚁 DroneEduAI                 ● Connected  🔋 Battery  ◉ AV         │
  ├───────────────────────────── content ─────────────────────────────────┤
  │  [ AI BLOCK 55% ]   │   [ MISSION BUILDER 45% ]                       │
  ├───────────────────────────── status bar ──────────────────────────────┤
  │  Simulator: Running  AI Model: MediaPipe   Telemetry: Connected  FPS  │
  └───────────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap
import os

import config
from ui.mission_builder import MissionBuilder


# ────────────────────────────────────────────────────────────────────────────
# Header bar
# ────────────────────────────────────────────────────────────────────────────
class HeaderBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setObjectName("headerBar")
        self.setStyleSheet(f"""
            QFrame#headerBar {{
                background: {config.COLOR_CARD};
                border-bottom: 1px solid {config.COLOR_BORDER};
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)

        # Logo icon + title
        logo_icon = QLabel()
        logo_path = os.path.join(config.ICONS_DIR, "drone.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo_icon.setPixmap(pix.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo_icon.setText("🚁")
            logo_icon.setStyleSheet("font-size: 22px;")
        lay.addWidget(logo_icon)

        title = QLabel("Drone Edu AI")
        title.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 17px; font-weight: 700; letter-spacing: 0.5px;"
        )
        lay.addWidget(title)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(20)
        div.setStyleSheet(f"color: {config.COLOR_BORDER};")
        lay.addWidget(div)

        page_lbl = QLabel("Mission Builder")
        page_lbl.setStyleSheet(f"color: {config.COLOR_ACCENT}; font-size: 12px; font-weight: 600;")
        lay.addWidget(page_lbl)

        lay.addStretch()

        # Connection status
        self._conn_dot = QLabel("●")
        self._conn_dot.setStyleSheet(f"color: {config.COLOR_DANGER}; font-size: 14px;")
        self._conn_lbl = QLabel("Disconnected")
        self._conn_lbl.setStyleSheet(f"color: {config.COLOR_TEXT}; font-size: 12px; font-weight: 600;")
        lay.addWidget(self._conn_dot)
        lay.addWidget(self._conn_lbl)

        self._sep1 = self._sep(lay)

        # Battery
        self._batt = QLabel("🔋 100%")
        self._batt.setStyleSheet(f"color: {config.COLOR_TEXT}; font-size: 12px;")
        lay.addWidget(self._batt)
        self._batt.hide()

        self._sep2 = self._sep(lay)
        self._sep2.hide()

        # Telemetry
        self._telem = QLabel("Telemetry")
        self._telem.setStyleSheet(
            f"color: {config.COLOR_SUCCESS}; font-size: 11px; font-weight: 600; "
            f"background: {config.COLOR_SUCCESS}22; border-radius: 5px; padding: 2px 8px;"
        )
        lay.addWidget(self._telem)
        self._telem.hide()

        self._sep3 = self._sep(lay)
        self._sep3.hide()

        # Avatar
        avatar = QLabel("AV")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background: {config.COLOR_ACCENT}; color: {config.COLOR_TEXT}; "
            f"border-radius: 16px; font-size: 12px; font-weight: 700;"
        )
        lay.addWidget(avatar)

    @staticmethod
    def _sep(lay: QHBoxLayout) -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(18)
        div.setStyleSheet(f"color: {config.COLOR_BORDER};")
        lay.addWidget(div)
        return div

    def update_connection(self, connected: bool, label: str) -> None:
        color = config.COLOR_SUCCESS if connected else config.COLOR_DANGER
        self._conn_dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        self._conn_lbl.setText(label)
        self._batt.setVisible(connected)
        self._telem.setVisible(connected)
        self._sep2.setVisible(connected)
        self._sep3.setVisible(connected)


# ────────────────────────────────────────────────────────────────────────────
# Status bar (bottom)
# ────────────────────────────────────────────────────────────────────────────
class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setObjectName("statusBar")
        self.setStyleSheet(f"""
            QFrame#statusBar {{
                background: {config.COLOR_CARD};
                border-top: 1px solid {config.COLOR_BORDER};
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(16)

        self._sim_lbl   = self._chip("Simulator:", "Stopped",   config.COLOR_MUTED)
        self._model_lbl = self._chip("AI Model:",  "MediaPipe", config.COLOR_INFO)
        lay.addLayout(self._sim_lbl[0])
        lay.addLayout(self._model_lbl[0])
        lay.addStretch()

        self._telem_lbl = self._chip("Telemetry:", "Disconnected", config.COLOR_DANGER)
        self._mav_lbl   = self._chip("MAVLink:",   "Inactive",    config.COLOR_DANGER)
        self._fps_lbl   = self._chip("FPS:",        "—",         config.COLOR_SUBTEXT)
        lay.addLayout(self._telem_lbl[0])
        lay.addLayout(self._mav_lbl[0])
        lay.addLayout(self._fps_lbl[0])

        self._sim_value = self._sim_lbl[1]
        self._telem_value = self._telem_lbl[1]
        self._mav_value = self._mav_lbl[1]
        self._fps_value = self._fps_lbl[1]

    @staticmethod
    def _chip(prefix: str, value: str, color: str):
        row = QHBoxLayout()
        row.setSpacing(4)
        p = QLabel(prefix)
        p.setStyleSheet(f"color: {config.COLOR_TEXT}; font-size: 11px;")
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")
        row.addWidget(p)
        row.addWidget(v)
        return row, v

    def set_simulator_running(self, running: bool) -> None:
        if running:
            self._sim_value.setText("Running")
            self._sim_value.setStyleSheet(f"color: {config.COLOR_SUCCESS}; font-size: 11px; font-weight: 700;")
        else:
            self._sim_value.setText("Stopped")
            self._sim_value.setStyleSheet(f"color: {config.COLOR_MUTED}; font-size: 11px; font-weight: 700;")

    def update_connection(self, connected: bool) -> None:
        color = config.COLOR_SUCCESS if connected else config.COLOR_DANGER
        text = "Connected" if connected else "Disconnected"
        self._telem_value.setText(text)
        self._telem_value.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")
        self._mav_value.setText("Active" if connected else "Inactive")
        self._mav_value.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")

    def update_fps(self, fps: float) -> None:
        self._fps_value.setText(f"{fps:.1f}")


# ────────────────────────────────────────────────────────────────────────────
# Main Window
# ────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Edu AI — Mission Builder")
        logo_path = os.path.join(config.ICONS_DIR, "drone.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
            
        self._apply_theme()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Header
        self._header = HeaderBar()
        main_lay.addWidget(self._header)

        # Content
        self._builder = MissionBuilder()
        main_lay.addWidget(self._builder)

        # Status bar
        self._status = StatusBar()
        main_lay.addWidget(self._status)

        # Wire MAVLink → header
        self._builder.mavlink_controller.connection_changed.connect(
            self._header.update_connection
        )
        self._builder.mavlink_controller.connection_changed.connect(
            lambda connected, label: self._status.update_connection(connected)
        )

        # Wire MissionPanel → status
        self._builder.mission_panel.run_requested.connect(
            lambda: self._status.set_simulator_running(True)
        )
        self._builder.mission_panel.stop_requested.connect(
            lambda: self._status.set_simulator_running(False)
        )

        # FPS timer (polls camera service)
        self._fps_timer = QTimer(self)
        self._fps_timer.setInterval(500)
        self._fps_timer.timeout.connect(self._refresh_fps)
        self._fps_timer.start()

    # ------------------------------------------------------------------
    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {config.COLOR_BG};
                color: {config.COLOR_TEXT};
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }}
            /* Labels are transparent so the parent frame background shows through,
               preventing the #0F172A body color from bleeding into #1E293B cards */
            QLabel {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {config.COLOR_CARD};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {config.COLOR_BORDER};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0px; }}
            QToolTip {{
                background: {config.COLOR_CARD};
                color: {config.COLOR_TEXT};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 8px;
            }}
        """)

    def _refresh_fps(self) -> None:
        svc = self._builder._camera
        if svc.isRunning():
            self._status.update_fps(svc._fps)

    def closeEvent(self, event) -> None:
        self._builder.shutdown()
        super().closeEvent(event)
