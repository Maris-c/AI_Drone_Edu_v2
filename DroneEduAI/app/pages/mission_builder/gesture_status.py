import time
from PySide6.QtWidgets import (
    QFrame, QLabel, QProgressBar, QHBoxLayout, QVBoxLayout, QWidget
)
from PySide6.QtCore import Qt, Signal


class GestureStatusWidget(QFrame):
    """
    AI Progress section directly below the camera.
    Shows:
      - Current gesture name + confidence
      - A green progress bar (0→100%) over 5 seconds
    Emits gesture_confirmed when 100% is reached.
    After confirming, auto-resets for the next gesture.
    """
    gesture_confirmed = Signal(str)   # Emits confirmed gesture name

    HOLD_DURATION = 5.0               # seconds to confirm a gesture
    CONFIDENCE_THRESHOLD = 65.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        self.active_gesture  = "None"
        self.last_gesture    = "None"
        self.confidence      = 0.0
        self.start_time      = 0.0
        self.has_fired       = False
        self.gesture_hold_duration = self.HOLD_DURATION

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Section title
        lbl_section = QLabel("GESTURE RECOGNITION PROGRESS", self)
        lbl_section.setObjectName("lbl-section")
        layout.addWidget(lbl_section)

        # Gesture info row
        info_row = QWidget(self)
        info_row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(info_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        self.lbl_gesture = QLabel("Scanning…", self)
        self.lbl_gesture.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #F8FAFC; background: transparent;"
        )

        self.lbl_stats = QLabel("", self)
        self.lbl_stats.setStyleSheet(
            "font-size: 11px; color: #94A3B8; background: transparent;"
        )
        self.lbl_stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row_layout.addWidget(self.lbl_gesture, 1)
        row_layout.addWidget(self.lbl_stats)
        layout.addWidget(info_row)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

    # ── Main update method ────────────────────────────────────────────
    def set_gesture_reading(self, gesture: str, confidence: float):
        """
        Called every frame from MissionBuilderPage.
        Drives the stability progress bar.
        """
        self.confidence    = confidence
        self.active_gesture = gesture

        # Reset conditions
        if gesture == "None" or confidence < self.CONFIDENCE_THRESHOLD:
            self._reset_progress()
            return

        curr_time = time.time()

        # Gesture switched → restart timer
        if self.active_gesture != self.last_gesture:
            self.start_time     = curr_time
            self.last_gesture   = self.active_gesture
            self.has_fired      = False
            self.progress_bar.setValue(0)
            return

        # Stable gesture – update timer
        if self.start_time == 0.0:
            self.start_time = curr_time

        elapsed  = curr_time - self.start_time
        progress = min(100, int((elapsed / self.gesture_hold_duration) * 100))
        self.progress_bar.setValue(progress)

        self.lbl_gesture.setText(f"  {self.active_gesture}")
        self.lbl_stats.setText(
            f"Conf {confidence:.0f}%  ·  {elapsed:.1f}s / {self.gesture_hold_duration:.0f}s"
        )

        # Fire at 100%
        if progress >= 100 and not self.has_fired:
            self.has_fired = True
            self.gesture_confirmed.emit(self.active_gesture)
            # Auto-reset after short delay so next gesture can be captured
            self._post_confirm_reset()

    def _reset_progress(self):
        self.start_time = 0.0
        self.has_fired  = False
        self.progress_bar.setValue(0)
        self.lbl_gesture.setText("Scanning…")
        self.lbl_stats.setText("")

    def _post_confirm_reset(self):
        """Reset tracking state so next gesture can be detected immediately."""
        self.start_time   = 0.0
        self.has_fired    = False
        self.last_gesture = "__confirmed__"   # sentinel so next gesture starts fresh
        # Keep progress at 100% visually for one cycle, then it auto drops on next frame
