"""
MissionBuilder — root layout widget.

Wires together:
  • AIPanel        (left, 55%)
  • MissionPanel   (right, 45%)
  • All controllers + camera service
"""
from __future__ import annotations
import numpy as np

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter, QFrame
from PySide6.QtCore import Qt

from ui.ai_panel import AIPanel
from ui.mission_panel import MissionPanel
from controllers.gesture_controller import GestureController
from controllers.mission_controller import MissionController
from controllers.mavlink_controller import MAVLinkController
from services.mediapipe_service import MediaPipeService
import config


class MissionBuilder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Controllers ──────────────────────────────────────────────────
        self._mavlink  = MAVLinkController(self)
        self._mission  = MissionController(self)
        self._gesture  = GestureController(self)
        self._camera   = MediaPipeService(config.DEFAULT_CAMERA_INDEX, self)

        self._build_ui()
        self._wire_signals()
        # NOTE: MAVLink connects via the panel UI — no auto-connect on startup

    # ── Build ────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {config.COLOR_BORDER};
            }}
        """)

        # Left panel
        self.ai_panel = AIPanel()
        self.ai_panel.setMinimumWidth(380)

        # Right panel — pass mavlink controller so it can embed MAVLinkPanel
        self.mission_panel = MissionPanel(self._mission, self._mavlink)
        self.mission_panel.setMinimumWidth(300)

        splitter.addWidget(self.ai_panel)
        splitter.addWidget(self.mission_panel)

        # 55 / 45 split
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)

        root.addWidget(splitter)

    # ── Signal wiring ────────────────────────────────────────────────────
    def _wire_signals(self) -> None:
        # Camera service → AI panel (frames + quality)
        self._camera.frame_ready.connect(self.ai_panel.update_camera_frame)
        self._camera.quality_updated.connect(self.ai_panel.update_quality)
        self._camera.model_status.connect(self.ai_panel.on_model_status)

        # Camera service → gesture controller (gesture + quality gate)
        self._camera.gesture_detected.connect(self._gesture.on_gesture)
        self._camera.quality_updated.connect(self._gesture.on_quality_update)  # quality gate

        # AI panel → camera service control
        self.ai_panel.camera_toggle_requested.connect(self._on_camera_toggle)
        self.ai_panel.model_path_changed.connect(self._on_model_path_changed)

        # Gesture controller → AI panel (progress)
        self._gesture.progress_updated.connect(self.ai_panel.update_progress)
        self._gesture.current_gesture_changed.connect(self.ai_panel.update_current_gesture)
        self._gesture.gesture_confirmed.connect(self.ai_panel.on_gesture_confirmed)

        # Gesture controller → mission controller
        self._gesture.gesture_confirmed.connect(self._mission.add_gesture)

        # Mission controller → mission panel
        self._mission.block_added.connect(self.mission_panel.add_block)
        self._mission.block_updated.connect(self.mission_panel.update_block)
        self._mission.mission_cleared.connect(self.mission_panel.clear_blocks)
        self._mission.mission_loaded.connect(self.mission_panel.load_blocks)
        self._mission.validation_warning.connect(self.mission_panel.show_warning)
        self._mission.validation_cleared.connect(self.mission_panel.clear_warning)

        # Mission panel run/stop → MAVLink
        self.mission_panel.run_requested.connect(self._on_run_mission)
        self.mission_panel.stop_requested.connect(self._mavlink.stop_mission)

        # MAVLink → header bar (connection dot)
        self._mavlink.connection_changed.connect(
            self._get_header_update
        )

    # ── Slots ────────────────────────────────────────────────────────────
    def _on_camera_toggle(self, start: bool) -> None:
        if start:
            if not self._camera.isRunning():
                self._camera.start_service()
        else:
            self._camera.stop_service()
            self._gesture.set_enabled(False)
            self._gesture.set_enabled(True)

    def _on_model_path_changed(self, path: str) -> None:
        self._camera.update_model_path(path)

    def _on_run_mission(self) -> None:
        self._mavlink.run_mission(self._mission.blocks())

    def _get_header_update(self) -> object:
        """Return the header update slot (resolved at runtime to avoid circular import)."""
        # The MainWindow wires connection_changed → header bar separately.
        pass

    # ── Cleanup ──────────────────────────────────────────────────────────
    def shutdown(self) -> None:
        if self._camera.isRunning():
            self._camera.stop_service()

    # ── Status accessors for the bottom status bar ───────────────────────
    @property
    def mavlink_controller(self) -> MAVLinkController:
        return self._mavlink
