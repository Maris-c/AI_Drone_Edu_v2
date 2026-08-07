"""
GestureController — 5-second gesture verification state machine.

Flow:
  MediaPipeService emits gesture_detected(name, conf)
        ↓
  GestureController.on_gesture()
        ↓   (same gesture + conf > threshold for 5 s)
  gesture_confirmed(name) → MissionController.add_gesture()
"""
from __future__ import annotations
from PySide6.QtCore import QObject, Signal, QTimer

import config


class GestureController(QObject):
    progress_updated        = Signal(int)   # 0–100
    gesture_confirmed       = Signal(str)   # confirmed gesture name
    current_gesture_changed = Signal(str)   # live gesture label for UI

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._current: str    = ""
        self._elapsed_ms: int  = 0
        self._enabled: bool    = True
        self._quality_ok: bool = False  # must be True (all quality checks pass) to allow progress

        self._timer = QTimer(self)
        self._timer.setInterval(config.GESTURE_PROGRESS_UPDATE_INTERVAL)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------
    # Slot: connected to MediaPipeService.gesture_detected
    # ------------------------------------------------------------------
    def on_gesture(self, gesture_name: str, confidence: float) -> None:
        if not self._enabled:
            return

        # Quality gate: all checks must pass before we allow progress
        if not self._quality_ok:
            self._reset()
            return

        # Bad state: no valid gesture
        if gesture_name in ("No Hand", "No Model", "Error", "") or \
                confidence < config.GESTURE_CONFIDENCE_THRESHOLD:
            self._reset()
            return

        if gesture_name != self._current:
            # New gesture detected → restart timer
            self._current = gesture_name
            self._elapsed_ms = 0
            self.current_gesture_changed.emit(gesture_name)
            if not self._timer.isActive():
                self._timer.start()
        # else: same gesture continues → let _tick run

    # ------------------------------------------------------------------
    # Slot: connected to MediaPipeService.quality_updated
    # ------------------------------------------------------------------
    def on_quality_update(self, metrics: dict) -> None:
        """Allow progress only when every quality metric is 'good'.
        If quality drops while progress is running, reset immediately."""
        all_good = all(d.get("status") == "good" for d in metrics.values())
        self._quality_ok = all_good
        if not all_good and self._timer.isActive():
            self._reset()

    # ------------------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._reset()

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        if not self._current:
            return

        self._elapsed_ms += config.GESTURE_PROGRESS_UPDATE_INTERVAL
        pct = min(int(self._elapsed_ms * 100 / config.GESTURE_CONFIRM_DURATION_MS), 100)
        self.progress_updated.emit(pct)

        if pct >= 100:
            confirmed = self._current
            self._reset()
            self.gesture_confirmed.emit(confirmed)

    def _reset(self) -> None:
        self._timer.stop()
        self._elapsed_ms = 0
        self._current    = ""
        self.progress_updated.emit(0)
