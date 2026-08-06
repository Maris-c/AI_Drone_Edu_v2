import os
import cv2
import numpy as np

from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QSizePolicy, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QFont


class CameraPreviewWidget(QFrame):
    """
    Left-panel camera card.
    Contains:
      - AI model file selector (top)
      - Camera viewport with 4:3 aspect ratio + purple border + ROI overlay
      - Camera ON/OFF toggle (top-right of viewport)
    """
    camera_toggled   = Signal(bool)    # True = on, False = off
    model_path_changed = Signal(str)   # Emits new model file path

    # ── Init ──────────────────────────────────────────────────────────
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.is_camera_on  = False
        self.latest_frame  = None
        self.landmarks     = []
        self.hand_box      = None
        self.roi_bounds    = None
        self.gesture_name  = "None"
        self.confidence    = 0.0
        self.fps           = 0.0

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Section Label ─────────────────────────────────────────────
        lbl_section = QLabel("CAMERA FEED", self)
        lbl_section.setObjectName("lbl-section")
        layout.addWidget(lbl_section)

        # ── AI Model Selector ─────────────────────────────────────────
        model_row = QWidget(self)
        model_row.setStyleSheet("background: transparent;")
        mr_layout = QHBoxLayout(model_row)
        mr_layout.setContentsMargins(0, 0, 0, 0)
        mr_layout.setSpacing(8)

        lbl_model = QLabel("AI Model:", self)
        lbl_model.setStyleSheet("font-size: 11px; color: #94A3B8; background: transparent;")
        lbl_model.setFixedWidth(58)

        self.model_path_edit = QLineEdit(self)
        self.model_path_edit.setPlaceholderText("Select gesture model (.pkl) …")
        self.model_path_edit.setReadOnly(True)
        self.model_path_edit.setStyleSheet("""
            QLineEdit {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                color: #94A3B8;
                font-size: 11px;
            }
        """)

        self.btn_browse = QPushButton("Browse", self)
        self.btn_browse.setFixedWidth(64)
        self.btn_browse.setFixedHeight(28)
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #8B5CF6;
                color: #F8FAFC;
            }
        """)
        self.btn_browse.clicked.connect(self._browse_model)

        mr_layout.addWidget(lbl_model)
        mr_layout.addWidget(self.model_path_edit, 1)
        mr_layout.addWidget(self.btn_browse)
        layout.addWidget(model_row)

        # ── Camera Viewport ───────────────────────────────────────────
        self.viewport_frame = QFrame(self)
        self.viewport_frame.setObjectName("cam_viewport")
        self.viewport_frame.setStyleSheet("""
            QFrame#cam_viewport {
                background-color: #080D1A;
                border: 2px solid #8B5CF6;
                border-radius: 10px;
            }
        """)
        vf_layout = QVBoxLayout(self.viewport_frame)
        vf_layout.setContentsMargins(0, 0, 0, 0)
        vf_layout.setSpacing(0)

        # Header row inside viewport (status + toggle button)
        hdr = QWidget(self.viewport_frame)
        hdr.setStyleSheet("background: transparent;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(10, 6, 10, 0)

        self.status_lbl = QLabel("● Offline", hdr)
        self.status_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #475569; background: transparent;"
        )
        hdr_lay.addWidget(self.status_lbl)
        hdr_lay.addStretch()

        self.btn_toggle = QPushButton("Camera ON", hdr)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setFixedSize(90, 26)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 5px;
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { border-color: #8B5CF6; color: #F8FAFC; }
            QPushButton:checked {
                background: #8B5CF6;
                border: none;
                color: #FFFFFF;
            }
        """)
        self.btn_toggle.clicked.connect(self._on_toggle)
        hdr_lay.addWidget(self.btn_toggle)

        vf_layout.addWidget(hdr)

        # Video label
        self.video_label = QLabel(self.viewport_frame)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._show_placeholder()
        vf_layout.addWidget(self.video_label, 1)

        # Keep 4:3 aspect by fixed-policy on the frame
        self.viewport_frame.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.MinimumExpanding
        )
        self.viewport_frame.setMinimumHeight(240)

        layout.addWidget(self.viewport_frame, 1)

    # ── Placeholder ───────────────────────────────────────────────────
    def _show_placeholder(self):
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText(
            "📷  Place your hand inside the frame"
        )
        self.video_label.setStyleSheet(
            "color: #475569; font-size: 13px; font-weight: 500; "
            "background: transparent;"
        )

    # ── Toggle Slot ───────────────────────────────────────────────────
    def _on_toggle(self, checked: bool):
        self.is_camera_on = checked
        if checked:
            self.btn_toggle.setText("Camera OFF")
            self.status_lbl.setText("● Live")
            self.status_lbl.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #22C55E; background: transparent;"
            )
            self.video_label.setStyleSheet("background: transparent;")
            self.video_label.setText("")
        else:
            self.btn_toggle.setText("Camera ON")
            self.status_lbl.setText("● Offline")
            self.status_lbl.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #475569; background: transparent;"
            )
            self._show_placeholder()
            self.latest_frame = None
        self.camera_toggled.emit(checked)

    # ── Browse Model ──────────────────────────────────────────────────
    def _browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Gesture Model",
            "",
            "Model Files (*.pkl *.h5 *.onnx);;All Files (*)",
        )
        if path:
            self.model_path_edit.setText(path)
            self.model_path_edit.setToolTip(path)
            self.model_path_changed.emit(path)

    # ── Frame Update ──────────────────────────────────────────────────
    def update_frame(self, bgr_frame, landmarks=None, hand_box=None,
                     roi_bounds=None, gesture="None", confidence=0.0, fps=0.0):
        if not self.is_camera_on:
            return

        self.landmarks    = landmarks or []
        self.hand_box     = hand_box
        self.roi_bounds   = roi_bounds
        self.gesture_name = gesture
        self.confidence   = confidence
        self.fps          = fps

        h, w, ch = bgr_frame.shape
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        self._draw_hud(rgb)

        qimg = QImage(rgb.data, w, h, w * ch, QImage.Format_RGB888).copy()
        scaled = QPixmap.fromImage(qimg).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    # ── HUD Drawing (OpenCV) ──────────────────────────────────────────
    def _draw_hud(self, frame: np.ndarray):
        h, w, _ = frame.shape

        # ROI corners
        if self.roi_bounds:
            x1, y1, x2, y2 = self.roi_bounds
            col = (139, 92, 246) if self.hand_box else (51, 65, 85)  # purple / slate
            cl = 18
            for (sx, sy, ex, ey) in [
                (x1, y1, x1+cl, y1), (x1, y1, x1, y1+cl),
                (x2, y1, x2-cl, y1), (x2, y1, x2, y1+cl),
                (x1, y2, x1+cl, y2), (x1, y2, x1, y2-cl),
                (x2, y2, x2-cl, y2), (x2, y2, x2, y2-cl),
            ]:
                cv2.line(frame, (sx, sy), (ex, ey), col, 2)

        # Hand box + label
        if self.hand_box:
            xb1, yb1, xb2, yb2 = self.hand_box
            cv2.rectangle(frame, (xb1, yb1), (xb2, yb2), (56, 189, 248), 1)
            label = f"{self.gesture_name}  {self.confidence:.0f}%"
            cv2.putText(frame, label, (xb1, max(yb1 - 8, 18)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (56, 189, 248), 1, cv2.LINE_AA)

        # Landmarks skeleton
        if self.landmarks:
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in self.landmarks]
            connections = [
                (0,1),(1,2),(2,3),(3,4),
                (0,5),(5,6),(6,7),(7,8),
                (5,9),(9,10),(10,11),(11,12),
                (9,13),(13,14),(14,15),(15,16),
                (13,17),(17,18),(18,19),(19,20),(0,17),
            ]
            for a, b in connections:
                if a < len(pts) and b < len(pts):
                    cv2.line(frame, pts[a], pts[b], (139, 92, 246), 1)
            for i, pt in enumerate(pts):
                col = (56, 189, 248) if i in [4, 8, 12, 16, 20] else (34, 197, 94)
                cv2.circle(frame, pt, 4, col, -1)

        # HUD metrics
        cv2.putText(frame, f"FPS {self.fps:.1f}", (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (71, 85, 105), 1, cv2.LINE_AA)
        status_txt = "TARGET LOCK" if self.hand_box else "SEARCHING..."
        status_col = (34, 197, 94) if self.hand_box else (71, 85, 105)
        cv2.putText(frame, status_txt, (w - 110, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, status_col, 1, cv2.LINE_AA)
