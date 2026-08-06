from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QBrush


# ── Status Icon Dot ───────────────────────────────────────────────────
class _StatusDot(QWidget):
    """Tiny coloured circle indicator."""
    COLOR_GOOD    = "#22C55E"
    COLOR_WARN    = "#F59E0B"
    COLOR_BAD     = "#EF4444"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(self.COLOR_BAD)
        self.setFixedSize(10, 10)

    def set_status(self, level: str):
        """level: 'good' | 'warning' | 'bad'"""
        if level == "good":
            self._color = QColor(self.COLOR_GOOD)
        elif level == "warning":
            self._color = QColor(self.COLOR_WARN)
        else:
            self._color = QColor(self.COLOR_BAD)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(0, 0, 10, 10)
        p.end()


# ── Status Icon Label ─────────────────────────────────────────────────
def _icon_for_level(level: str) -> str:
    return {"good": "✓", "warning": "⚠", "bad": "✗"}.get(level, "✗")

def _color_for_level(level: str) -> str:
    return {
        "good":    "#22C55E",
        "warning": "#F59E0B",
        "bad":     "#EF4444",
    }.get(level, "#EF4444")


# ── Single Check Row ──────────────────────────────────────────────────
class _CheckRow(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(8)

        self.icon_lbl = QLabel("✗", self)
        self.icon_lbl.setFixedWidth(16)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #EF4444; background: transparent;")

        self.name_lbl = QLabel(label, self)
        self.name_lbl.setStyleSheet("font-size: 12px; color: #CBD5E1; background: transparent;")

        self.val_lbl = QLabel("—", self)
        self.val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8; background: transparent;")

        row.addWidget(self.icon_lbl)
        row.addWidget(self.name_lbl, 1)
        row.addWidget(self.val_lbl)

    def update_status(self, value: str, level: str):
        icon  = _icon_for_level(level)
        color = _color_for_level(level)
        self.icon_lbl.setText(icon)
        self.icon_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {color}; background: transparent;"
        )
        self.val_lbl.setText(value)
        self.val_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {color}; background: transparent;"
        )


# ── Main Widget ───────────────────────────────────────────────────────
class CameraQualityChecksWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        lbl_section = QLabel("QUALITY CHECK", self)
        lbl_section.setObjectName("lbl-section")
        layout.addWidget(lbl_section)

        # Six rows per spec
        self.row_brightness = _CheckRow("Brightness",     self)
        self.row_blur       = _CheckRow("Blur Detection", self)
        self.row_hand       = _CheckRow("Hand Detection", self)
        self.row_roi        = _CheckRow("ROI Validation", self)
        self.row_fps        = _CheckRow("FPS",            self)
        self.row_conf       = _CheckRow("Confidence",     self)

        for row in (self.row_brightness, self.row_blur, self.row_hand,
                    self.row_roi, self.row_fps, self.row_conf):
            layout.addWidget(row)

        self.reset_checks()

    # ── Reset ─────────────────────────────────────────────────────────
    def reset_checks(self):
        self.row_brightness.update_status("Pending",  "warning")
        self.row_blur.update_status("Pending",        "warning")
        self.row_hand.update_status("No Hand",        "bad")
        self.row_roi.update_status("N/A",             "bad")
        self.row_fps.update_status("0.0 fps",         "warning")
        self.row_conf.update_status("0%",             "bad")

    # ── Update Diagnostics ────────────────────────────────────────────
    def update_diagnostics(self, data: dict):
        """
        Accepts quality dict from MediaPipeService.process_frame().
        Keys: brightness, blur, hand_detected, roi_alignment, lighting, distance
        Extra keys added by MissionBuilderPage: fps, confidence
        """
        # Brightness
        b = data.get("brightness", "Pending")
        self.row_brightness.update_status(b, "good" if b == "Good" else "warning")

        # Blur
        bl = data.get("blur", "Pending")
        self.row_blur.update_status(bl, "good" if bl == "Good" else "bad")

        # Hand detection
        h = data.get("hand_detected", "No Hand")
        detected = h == "Good"
        self.row_hand.update_status(
            "Detected" if detected else "No Hand",
            "good" if detected else "bad"
        )

        # ROI Validation
        r = data.get("roi_alignment", "N/A")
        if r == "Good":
            lvl = "good"
        elif r in ("Out of Bounds", "Empty"):
            lvl = "warning"
        else:
            lvl = "bad"
        self.row_roi.update_status(r, lvl)

        # FPS
        fps_val = data.get("fps", 0.0)
        if isinstance(fps_val, (int, float)):
            fps_str = f"{fps_val:.1f} fps"
            fps_lvl = "good" if fps_val >= 20 else ("warning" if fps_val >= 10 else "bad")
        else:
            fps_str = str(fps_val)
            fps_lvl = "warning"
        self.row_fps.update_status(fps_str, fps_lvl)

        # Confidence
        conf_val = data.get("confidence", 0.0)
        if isinstance(conf_val, (int, float)):
            conf_str = f"{conf_val:.0f}%"
            conf_lvl = "good" if conf_val >= 75 else ("warning" if conf_val >= 50 else "bad")
        else:
            conf_str = str(conf_val)
            conf_lvl = "warning"
        self.row_conf.update_status(conf_str, conf_lvl)
