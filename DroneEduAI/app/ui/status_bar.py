from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt


class _StatusChip(QLabel):
    """A small styled chip showing 'Label: Value'."""
    def __init__(self, prefix: str, value: str = "—",
                 value_color: str = "#38BDF8", parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self._value  = value
        self._color  = value_color
        self._refresh()
        self.setStyleSheet("font-size: 11px; background: transparent;")

    def set_value(self, value: str, color: str | None = None):
        self._value = value
        if color:
            self._color = color
        self._refresh()

    def _refresh(self):
        self.setText(
            f"<span style='color:#94A3B8'>{self._prefix}</span> "
            f"<span style='color:{self._color}; font-weight:600'>{self._value}</span>"
        )


class CustomStatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusbar")
        self.setFixedHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(28)

        # Left items
        self.sim_status   = _StatusChip("Simulator",  "Idle",           "#94A3B8", self)
        self.model_status = _StatusChip("AI Model",   "MediaPipe Hands","#8B5CF6", self)
        self.fps_status   = _StatusChip("FPS",        "0.0",            "#F59E0B", self)

        layout.addWidget(self.sim_status)
        layout.addWidget(self.model_status)
        layout.addWidget(self.fps_status)

        # Spacer
        layout.addSpacerItem(
            QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        )

        # Right items
        self.tele_status = _StatusChip("Telemetry", "Disconnected", "#EF4444", self)
        self.mav_status  = _StatusChip("MAVLink",   "Inactive",     "#EF4444", self)
        self.ver_chip    = _StatusChip("v",          "1.0.0",        "#94A3B8", self)

        layout.addWidget(self.tele_status)
        layout.addWidget(self.mav_status)
        layout.addWidget(self.ver_chip)

    # ── Update Methods ────────────────────────────────────────────────
    def update_simulator(self, running: bool):
        if running:
            self.sim_status.set_value("Running", "#22C55E")
        else:
            self.sim_status.set_value("Idle", "#94A3B8")

    def update_fps(self, fps: float):
        color = "#22C55E" if fps >= 20 else ("#F59E0B" if fps >= 10 else "#EF4444")
        self.fps_status.set_value(f"{fps:.1f}", color)

    def update_telemetry(self, connected: bool):
        if connected:
            self.tele_status.set_value("Connected", "#22C55E")
        else:
            self.tele_status.set_value("Disconnected", "#EF4444")

    def update_mavlink(self, connected: bool):
        if connected:
            self.mav_status.set_value("Connected", "#22C55E")
        else:
            self.mav_status.set_value("Inactive", "#EF4444")
