import json
import os

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QScrollArea, QFrame, QLabel, QPushButton,
    QFileDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QColor

from app.pages.base_page import BasePage
from app.pages.mission_builder.camera_preview import CameraPreviewWidget
from app.pages.mission_builder.gesture_status import GestureStatusWidget
from app.pages.mission_builder.quality_checks import CameraQualityChecksWidget
from app.pages.mission_builder.gesture_library import GestureLibraryWidget
from app.pages.mission_builder.visual_programming import BlocklyCanvas
from app.pages.mission_builder.block_properties import BlockPropertiesPanel
from app.models.mission_model import MissionModel


# ─────────────────────────────────────────────────────────────────────
# Section Label Helper
# ─────────────────────────────────────────────────────────────────────
def _section_label(text: str, parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setStyleSheet("""
        font-size: 11px;
        font-weight: 700;
        color: #8B5CF6;
        letter-spacing: 2px;
        background: transparent;
        padding: 0;
    """)
    return lbl


# ─────────────────────────────────────────────────────────────────────
# Mission Toolbar
# ─────────────────────────────────────────────────────────────────────
class MissionToolbar(QWidget):
    """Bottom-right toolbar with Run / Stop / Clear / Export / Import."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ▶ Run Mission
        self.btn_run = QPushButton("▶  Run Mission", self)
        self.btn_run.setObjectName("btn-success")
        self.btn_run.setFixedHeight(34)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background: #22C55E;
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 12px;
                padding: 0 16px;
            }
            QPushButton:hover { background: #16A34A; }
            QPushButton:pressed { background: #15803D; }
        """)

        # ■ Stop
        self.btn_stop = QPushButton("■  Stop", self)
        self.btn_stop.setFixedHeight(34)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: #EF4444;
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover { background: #DC2626; }
            QPushButton:pressed { background: #B91C1C; }
        """)

        # 🗑 Clear
        self.btn_clear = QPushButton("🗑  Clear", self)
        self.btn_clear.setFixedHeight(34)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #94A3B8;
                font-weight: 600;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover { border-color: #EF4444; color: #EF4444; }
        """)

        # 📤 Export JSON
        self.btn_export = QPushButton("📤  Export JSON", self)
        self.btn_export.setFixedHeight(34)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #38BDF8;
                font-weight: 600;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover { border-color: #38BDF8; }
        """)

        # 📥 Import
        self.btn_import = QPushButton("📥  Import", self)
        self.btn_import.setFixedHeight(34)
        self.btn_import.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #94A3B8;
                font-weight: 600;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover { border-color: #8B5CF6; color: #C4B5FD; }
        """)

        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_clear)
        layout.addWidget(self.btn_export)
        layout.addWidget(self.btn_import)


# ─────────────────────────────────────────────────────────────────────
# Validation Warning Banner
# ─────────────────────────────────────────────────────────────────────
class ValidationBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(239,68,68,0.10);
                border: 1px solid #EF4444;
                border-radius: 8px;
            }
        """)
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        title = QLabel("⚠  Mission Warning", self)
        title.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #EF4444; background: transparent;"
        )
        layout.addWidget(title)

        self.lbl_msg = QLabel("", self)
        self.lbl_msg.setStyleSheet(
            "font-size: 11px; color: #FCA5A5; background: transparent;"
        )
        self.lbl_msg.setWordWrap(True)
        layout.addWidget(self.lbl_msg)

    def show_warnings(self, warnings: list[str]):
        if warnings:
            self.lbl_msg.setText("\n".join(warnings))
            self.setVisible(True)
        else:
            self.setVisible(False)


# ─────────────────────────────────────────────────────────────────────
# Mission Builder Page
# ─────────────────────────────────────────────────────────────────────
class MissionBuilderPage(BasePage):
    def __init__(self, camera_thread, mp_service, parent=None):
        super().__init__("Mission Builder", parent)
        self.camera_thread = camera_thread
        self.mp_service    = mp_service
        self.mission_model = MissionModel()

        self._setup_ui()
        self._connect_signals()

        # Load initial default mission
        self.canvas.load_mission(self.mission_model.blocks)

    # ─── UI Setup ────────────────────────────────────────────────────
    def _setup_ui(self):
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Root horizontal splitter
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setHandleWidth(1)

        # ── LEFT PANEL (55%) ──────────────────────────────────────────
        self.left_panel = QFrame(self)
        self.left_panel.setObjectName("left-panel")
        left_root = QVBoxLayout(self.left_panel)
        left_root.setContentsMargins(16, 16, 8, 16)
        left_root.setSpacing(0)

        # Section title
        left_root.addWidget(_section_label("⬡  AI BLOCK", self))
        left_root.addSpacing(10)

        # Scroll area containing all AI widgets
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self._scroll_layout = QVBoxLayout(scroll_content)
        self._scroll_layout.setContentsMargins(0, 0, 6, 0)
        self._scroll_layout.setSpacing(10)

        self.camera_preview  = CameraPreviewWidget(self)
        self.gesture_status  = GestureStatusWidget(self)
        self.quality_checks  = CameraQualityChecksWidget(self)
        self.gesture_library = GestureLibraryWidget(self)

        self._scroll_layout.addWidget(self.camera_preview)
        self._scroll_layout.addWidget(self.gesture_status)
        self._scroll_layout.addWidget(self.quality_checks)
        self._scroll_layout.addWidget(self.gesture_library)
        self._scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        left_root.addWidget(scroll, 1)

        # ── RIGHT PANEL (45%) ─────────────────────────────────────────
        self.right_panel = QFrame(self)
        self.right_panel.setObjectName("right-panel")
        right_root = QVBoxLayout(self.right_panel)
        right_root.setContentsMargins(8, 16, 16, 16)
        right_root.setSpacing(10)

        # Section title + block count chip
        title_row = QWidget(self)
        title_row.setStyleSheet("background: transparent;")
        tr_layout = QHBoxLayout(title_row)
        tr_layout.setContentsMargins(0, 0, 0, 0)
        tr_layout.setSpacing(10)
        tr_layout.addWidget(_section_label("⬡  MISSION BUILDER", self))
        tr_layout.addStretch()

        self.lbl_block_count = QLabel("0 blocks", self)
        self.lbl_block_count.setStyleSheet(
            "font-size: 10px; color: #475569; background: transparent;"
        )
        tr_layout.addWidget(self.lbl_block_count)
        right_root.addWidget(title_row)

        # Canvas + Properties side panel
        canvas_row = QWidget(self)
        canvas_row.setStyleSheet("background: transparent;")
        cr_layout = QHBoxLayout(canvas_row)
        cr_layout.setContentsMargins(0, 0, 0, 0)
        cr_layout.setSpacing(8)

        self.canvas = BlocklyCanvas(self)
        cr_layout.addWidget(self.canvas, 1)

        self.properties_panel = BlockPropertiesPanel(self)
        cr_layout.addWidget(self.properties_panel)

        right_root.addWidget(canvas_row, 1)

        # Validation warning banner
        self.validation_banner = ValidationBanner(self)
        right_root.addWidget(self.validation_banner)

        # Mission toolbar
        self.toolbar = MissionToolbar(self)
        right_root.addWidget(self.toolbar, 0, Qt.AlignRight)

        # Add panels to splitter (55 / 45)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)

        # Use stretch factors for 55/45
        self.splitter.setStretchFactor(0, 55)
        self.splitter.setStretchFactor(1, 45)

        self.main_layout.addWidget(self.splitter)

    # ─── Connect Signals ──────────────────────────────────────────────
    def _connect_signals(self):
        # Camera toggle
        self.camera_preview.camera_toggled.connect(self._on_camera_toggled)

        # Camera model path changed → pass to MediaPipe service
        self.camera_preview.model_path_changed.connect(self._on_model_path_changed)

        # Frame pipeline
        self.camera_thread.frame_updated.connect(self._on_frame_updated)

        # Gesture confirmed → auto-add block
        self.gesture_status.gesture_confirmed.connect(self._on_gesture_confirmed)

        # Gesture library click → add block
        self.gesture_library.gesture_selected.connect(self._on_gesture_selected)

        # Block selected in canvas → show properties
        self.canvas.block_selected.connect(self._on_block_selected)

        # Properties applied
        self.properties_panel.property_updated.connect(self._on_properties_applied)

        # Mission model changed → sync canvas
        self.mission_model.mission_changed.connect(self._sync_canvas)

        # Validation warnings
        self.mission_model.validation_warn.connect(self._on_validation_warn)

        # Toolbar buttons
        self.toolbar.btn_run.clicked.connect(self._on_run_mission)
        self.toolbar.btn_stop.clicked.connect(self._on_stop_mission)
        self.toolbar.btn_clear.clicked.connect(self._on_clear_mission)
        self.toolbar.btn_export.clicked.connect(self._on_export_mission)
        self.toolbar.btn_import.clicked.connect(self._on_import_mission)

    # ─── Camera Slots ─────────────────────────────────────────────────
    @Slot(bool)
    def _on_camera_toggled(self, checked: bool):
        if checked:
            self.camera_thread.start()
        else:
            self.camera_thread.stop()
            self.quality_checks.reset_checks()
            self.gesture_status.set_gesture_reading("None", 0.0)

    @Slot(str)
    def _on_model_path_changed(self, path: str):
        """Re-initialise MediaPipe classifier with user-selected model."""
        if hasattr(self.mp_service, "model_path"):
            self.mp_service.model_path = path
            self.mp_service.initialize_models()
            print(f"[MissionBuilder] AI model updated: {path}")

    @Slot(object)
    def _on_frame_updated(self, frame):
        gesture, conf, landmarks, box, roi, quality = \
            self.mp_service.process_frame(frame)

        # Inject FPS + confidence into quality dict for display
        quality["fps"]        = self.camera_thread.measured_fps
        quality["confidence"] = conf

        self.camera_preview.update_frame(
            bgr_frame=frame,
            landmarks=landmarks,
            hand_box=box,
            roi_bounds=roi,
            gesture=gesture,
            confidence=conf,
            fps=self.camera_thread.measured_fps,
        )
        self.gesture_status.set_gesture_reading(gesture, conf)
        self.quality_checks.update_diagnostics(quality)

    # ─── Gesture / Block Slots ────────────────────────────────────────
    @Slot(str)
    def _on_gesture_confirmed(self, gesture_name: str):
        print(f"[MissionBuilder] Gesture confirmed: {gesture_name}")
        self.mission_model.add_block(gesture_name, duration=2.0)

    @Slot(str, float)
    def _on_gesture_selected(self, block_name: str, duration: float):
        self.mission_model.add_block(block_name, duration=duration)

    @Slot(str)
    def _on_block_selected(self, block_id: str):
        for block in self.mission_model.blocks:
            if block.id == block_id:
                self.properties_panel.load_block_properties(block)
                break

    @Slot(str, float, str)
    def _on_properties_applied(self, block_id: str, duration: float, description: str):
        for block in self.mission_model.blocks:
            if block.id == block_id:
                block.duration = duration
                block.description = description
                block.parameters["duration"] = duration
                break
        self.mission_model.mission_changed.emit()

    # ─── Mission Canvas Sync ──────────────────────────────────────────
    def _sync_canvas(self):
        self.canvas.load_mission(self.mission_model.blocks)
        self.canvas.scroll_to_latest()

        # Update block count chip
        count = len(self.mission_model.blocks)
        noun = "block" if count == 1 else "blocks"
        self.lbl_block_count.setText(f"{count} {noun}")

        # Restore property panel
        cur_id = self.properties_panel.current_block_id
        if cur_id:
            found = False
            for block in self.mission_model.blocks:
                if block.id == cur_id:
                    self.properties_panel.load_block_properties(block)
                    found = True
                    break
            if not found:
                self.properties_panel.clear_selection()

    # ─── Validation ───────────────────────────────────────────────────
    @Slot(list)
    def _on_validation_warn(self, warnings: list):
        self.validation_banner.show_warnings(warnings)

    # ─── Toolbar Slots ────────────────────────────────────────────────
    @Slot()
    def _on_run_mission(self):
        warnings = self.mission_model.validate_mission()
        if warnings:
            QMessageBox.warning(
                self,
                "Mission Validation Failed",
                "Cannot run mission:\n\n" + "\n".join(warnings),
            )
            return
        print("[MissionBuilder] ▶ Running mission …")
        # TODO: wire to MAVLink controller

    @Slot()
    def _on_stop_mission(self):
        print("[MissionBuilder] ■ Mission stopped.")
        # TODO: wire to MAVLink controller

    @Slot()
    def _on_clear_mission(self):
        reply = QMessageBox.question(
            self,
            "Clear Mission",
            "Are you sure you want to clear all mission blocks?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.mission_model.clear_mission()
            self.properties_panel.clear_selection()

    @Slot()
    def _on_export_mission(self):
        json_str = self.mission_model.export_json()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Mission",
            "mission.json",
            "JSON Files (*.json)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)
            QMessageBox.information(
                self,
                "Export Successful",
                f"Mission exported to:\n{path}",
            )

    @Slot()
    def _on_import_mission(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Mission",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                json_str = f.read()
            success = self.mission_model.import_from_json(json_str)
            if success:
                self.properties_panel.clear_selection()
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Mission loaded from:\n{path}",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    "The selected file is not a valid mission JSON.",
                )
