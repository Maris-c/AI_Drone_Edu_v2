"""
AIPanel — Left panel (55 % width)

Layout order (per user request):
  1. Title: AI BLOCK
  2. Model path selector (Browse)
  3. Camera Feed  ← quality overlay on top-left of frame
  4. Gesture Recognition Progress
  5. Gesture Library
"""
from __future__ import annotations
import os

import cv2
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QGridLayout, QScrollArea, QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QRectF, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QPixmap, QImage,
    QLinearGradient, QBrush,
)

import config

try:
    from PySide6.QtSvg import QSvgRenderer
    _SVG_OK = True
except ImportError:
    _SVG_OK = False


# ────────────────────────────────────────────────────────────────────────────
# Quality overlay constants
# ────────────────────────────────────────────────────────────────────────────
_Q_STATUS_COLORS = {
    "good":    QColor("#22C55E"),
    "warning": QColor("#F59E0B"),
    "error":   QColor("#EF4444"),
}
_Q_GLYPHS = {"good": "✓", "warning": "⚠", "error": "✗"}


# ────────────────────────────────────────────────────────────────────────────
# Camera widget
# ────────────────────────────────────────────────────────────────────────────
class CameraWidget(QWidget):
    """Custom camera display: BGR frames + right-biased ROI overlay + quality overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._qimage: QImage | None = None   # raw frame — no QPixmap conversion
        self._quality_metrics: dict  = {}
        self._progress_pct: int = 0
        self._current_gesture: str = ""
        self._confirmed: bool = False
        self._paint_pending: bool = False    # drop-frame guard
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 240)

        # Floating progress overlay
        self._prog_overlay = QFrame(self)
        self._prog_overlay.setStyleSheet("background: rgba(30, 41, 59, 0.8); border-radius: 8px;")
        self._prog_overlay.setFixedSize(220, 60)
        self._prog_overlay.hide()
        
        olay = QVBoxLayout(self._prog_overlay)
        olay.setContentsMargins(10, 8, 10, 8)
        olay.setSpacing(4)
        
        self._prog_lbl = QLabel("")
        self._prog_lbl.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
        self._prog_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        olay.addWidget(self._prog_lbl)
        
        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, 100)
        self._prog_bar.setTextVisible(False)
        self._prog_bar.setFixedHeight(10)
        self._prog_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {config.COLOR_BORDER};
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {config.COLOR_SUCCESS}, stop:1 #16A34A);
                border-radius: 5px;
            }}
        """)
        olay.addWidget(self._prog_bar)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position the overlay at bottom center
        w = self._prog_overlay.width()
        h = self._prog_overlay.height()
        self._prog_overlay.setGeometry((self.width() - w) // 2, self.height() - h - 16, w, h)

    # ------------------------------------------------------------------
    def update_frame(self, bgr: np.ndarray) -> None:
        # Drop frame if the previous paint hasn't completed yet
        if self._paint_pending:
            return
        # Avoid cv2.cvtColor copy: use BGR_888 format and let Qt swap channels
        # via Format_BGR888 (available in Qt 5.14+ / Qt 6)
        h, w = bgr.shape[:2]
        bytes_per_line = w * 3
        self._qimage = QImage(
            bgr.data, w, h, bytes_per_line, QImage.Format.Format_BGR888
        ).copy()  # .copy() makes Qt own the buffer (thread-safe)
        self._paint_pending = True
        self.update()

    def clear_frame(self) -> None:
        self._qimage = None
        self._quality_metrics = {}
        self._paint_pending = False
        self.update()

    def update_quality_overlay(self, metrics: dict) -> None:
        """Receive quality data; painted on next paintEvent (no extra repaint)."""
        self._quality_metrics = metrics

    # ------------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        self._paint_pending = False
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        W, H = self.width(), self.height()

        if self._qimage and not self._qimage.isNull():
            iw, ih = self._qimage.width(), self._qimage.height()
            scale = min(W / iw, H / ih) if iw > 0 and ih > 0 else 1.0
            tw, th = int(iw * scale), int(ih * scale)
            ox = (W - tw) >> 1
            oy = (H - th) >> 1
            p.drawImage(QRect(ox, oy, tw, th), self._qimage)
            self._draw_roi_brackets(p, ox, oy, tw, th, tight=True)
            self._draw_quality_overlay(p, ox, oy, tw, th)
        else:
            self._draw_placeholder(p, W, H)

        p.end()

    # ------------------------------------------------------------------
    def _draw_placeholder(self, p: QPainter, W: int, H: int) -> None:
        p.fillRect(0, 0, W, H, QColor("#111827"))
        pen = QPen(QColor("#1a2744"), 1)
        p.setPen(pen)
        for x in range(0, W, 28):
            p.drawLine(x, 0, x, H)
        for y in range(0, H, 28):
            p.drawLine(0, y, W, y)
        self._draw_roi_brackets(p, 0, 0, W, H, tight=False)
        icon_font = QFont("Segoe UI Emoji", 28)
        p.setFont(icon_font)
        p.setPen(QPen(QColor("#334155")))
        p.drawText(QRect(0, H // 2 - 55, W, 50), Qt.AlignmentFlag.AlignCenter, "🖐")
        txt_font = QFont("Segoe UI", 9)
        p.setFont(txt_font)
        p.setPen(QPen(QColor("#475569")))
        p.drawText(
            QRect(0, H // 2 + 5, W, 30),
            Qt.AlignmentFlag.AlignCenter,
            "Place your right hand inside the frame",
        )

    def _draw_roi_brackets(
        self, p: QPainter, ox: int, oy: int, fw: int, fh: int, tight: bool
    ) -> None:
        """ROI shifted right (right-hand biased) and narrowed by ~20%."""
        if tight:
            # Left margin larger, right margin smaller → ROI sits in the right 60% of frame
            lx = int(fw * 0.28)
            rx = int(fw * 0.12)
            my = int(fh * 0.10)
        else:
            lx = int(fw * 0.32)
            rx = int(fw * 0.14)
            my = int(fh * 0.16)

        x1, y1 = ox + lx,       oy + my
        x2, y2 = ox + fw - rx,  oy + fh - my

        pen = QPen(QColor("#8B5CF6"), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRect(x1, y1, x2 - x1, y2 - y1)

        cs = 14
        pen2 = QPen(QColor("#8B5CF6"), 2, Qt.PenStyle.SolidLine)
        p.setPen(pen2)
        corners = [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]
        for cx, cy, dx, dy in corners:
            p.drawLine(cx, cy, cx + dx * cs, cy)
            p.drawLine(cx, cy, cx, cy + dy * cs)

    def _draw_quality_overlay(
        self, p: QPainter, ox: int, oy: int, fw: int, fh: int
    ) -> None:
        """Semi-transparent quality metrics panel over the top-left of the camera frame."""
        if not self._quality_metrics:
            return

        ROW_H   = 16
        PAD_X   = 7
        PAD_Y   = 5
        LABEL_W = 100   # left column: glyph + name
        VAL_W   = 42    # right column: value
        panel_w = PAD_X * 2 + LABEL_W + VAL_W
        panel_h = PAD_Y * 2 + len(self._quality_metrics) * ROW_H

        px = ox + 6
        py = oy + 6

        # Background
        p.fillRect(px, py, panel_w, panel_h, QColor(0, 0, 0, 155))

        font = QFont("Segoe UI", 7)
        p.setFont(font)

        for i, (name, data) in enumerate(self._quality_metrics.items()):
            status = data.get("status", "error")
            color  = _Q_STATUS_COLORS.get(status, QColor("#EF4444"))
            glyph  = _Q_GLYPHS.get(status, "✗")
            value  = data.get("value", "—")

            ty = py + PAD_Y + i * ROW_H + ROW_H - 3   # text baseline

            # Glyph + name
            p.setPen(QPen(color))
            p.drawText(px + PAD_X, ty, f"{glyph} {name}")

            # Value (right-aligned)
            p.setPen(QPen(QColor("#F8FAFC")))
            val_rect = QRect(px + PAD_X + LABEL_W, ty - ROW_H + 3, VAL_W, ROW_H)
            p.drawText(val_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, value)


# ────────────────────────────────────────────────────────────────────────────
# Gesture library card
# ────────────────────────────────────────────────────────────────────────────
def _load_svg_pixmap(path: str, size: int = 48) -> QPixmap | None:
    """Render an SVG into a square pixmap, preserving the SVG's aspect ratio."""
    if not _SVG_OK or not os.path.exists(path):
        return None
    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        return None

    default_size = renderer.defaultSize()
    if not default_size.isEmpty():
        ratio = default_size.width() / max(default_size.height(), 1)
        if ratio >= 1.0:
            w, h = size, max(1, int(size / ratio))
        else:
            h, w = size, max(1, int(size * ratio))
    else:
        w, h = size, size

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    pp = QPainter(pix)
    pp.setRenderHint(QPainter.RenderHint.Antialiasing)
    pp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    x_off = (size - w) // 2
    y_off = (size - h) // 2
    renderer.render(pp, QRectF(x_off, y_off, w, h))
    pp.end()
    return pix


class GestureCard(QFrame):
    clicked = Signal(str)

    def __init__(self, title: str, icon_path: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setObjectName("gestureCard")
        self.setFixedHeight(92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#gestureCard {{
                background: {config.COLOR_CARD};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 10px;
            }}
            QFrame#gestureCard:hover {{
                border: 1px solid {config.COLOR_ACCENT};
                background: #243352;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 6)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = _load_svg_pixmap(icon_path, 52)
        if pix:
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("✋")
            icon_lbl.setStyleSheet(f"color: {config.COLOR_ACCENT}; font-size: 26px;")
        lay.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(title)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 10px; font-weight: 600;"
        )
        lay.addWidget(name_lbl)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.title)
        super().mousePressEvent(event)


# ────────────────────────────────────────────────────────────────────────────
# Main AI Panel
# ────────────────────────────────────────────────────────────────────────────
class AIPanel(QWidget):
    camera_toggle_requested = Signal(bool)
    model_path_changed      = Signal(str)
    manual_gesture_added    = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera_on     = False
        self._current_gest  = ""
        self._cam_anim: QPropertyAnimation | None = None
        self._cam_body: QWidget | None = None   # the collapsible widget
        self._cam_body_h = 264                  # natural height (set after build)

        self._build_ui()

    # ── Build ────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        # ── 1. Title ──────────────────────────────────────────────────────
        title = QLabel("AI GESTURE")
        title.setStyleSheet(
            f"color: {config.COLOR_TEXT}; font-size: 16px; font-weight: 700; "
            f"border-left: 3px solid {config.COLOR_ACCENT}; padding-left: 10px;"
        )
        lay.addWidget(title)

        # ── 2. Model path (ABOVE camera) ──────────────────────────────────
        model_card = self._make_card()
        model_lay  = QHBoxLayout(model_card)
        model_lay.setContentsMargins(10, 8, 10, 8)
        model_lay.setSpacing(8)

        model_icon = QLabel("🤖")
        model_icon.setStyleSheet("font-size: 14px;")
        model_lay.addWidget(model_icon)

        self._model_path_lbl = QLabel(os.path.basename(config.DEFAULT_MODEL_PATH))
        self._model_path_lbl.setStyleSheet(
            f"color: {config.COLOR_SUBTEXT}; font-size: 11px;"
        )
        self._model_path_lbl.setToolTip(config.DEFAULT_MODEL_PATH)
        self._model_path_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        model_lay.addWidget(self._model_path_lbl)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(26)
        browse_btn.setFixedWidth(62)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(self._btn_style(config.COLOR_BORDER, small=True))
        browse_btn.clicked.connect(self._browse_model)
        model_lay.addWidget(browse_btn)

        lay.addWidget(model_card)

        # ── 3. Camera Feed + Quality overlay ─────────────────────────────
        cam_card = self._make_card()
        cam_lay  = QVBoxLayout(cam_card)
        cam_lay.setContentsMargins(10, 10, 10, 10)
        cam_lay.setSpacing(8)

        cam_header = QHBoxLayout()
        self._cam_status = QLabel("● Camera Feed")
        self._cam_status.setStyleSheet(f"color: {config.COLOR_MUTED}; font-size: 12px;")
        cam_header.addWidget(self._cam_status)
        cam_header.addStretch()
        self._cam_btn = QPushButton("Camera ON")
        self._cam_btn.setFixedHeight(28)
        self._cam_btn.setCheckable(True)
        self._cam_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cam_btn.setStyleSheet(self._btn_style(config.COLOR_ACCENT))
        self._cam_btn.toggled.connect(self._on_camera_toggled)
        cam_header.addWidget(self._cam_btn)
        cam_lay.addLayout(cam_header)

        # Camera widget body — wrapped in a container so we can animate its height
        self._cam_body = QWidget()
        self._cam_body.setObjectName("camBody")
        self._cam_body.setStyleSheet("QWidget#camBody { background: transparent; }")
        body_lay = QVBoxLayout(self._cam_body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        self.camera_widget = CameraWidget()
        self.camera_widget.setMinimumHeight(264)
        body_lay.addWidget(self.camera_widget)

        # Start collapsed (camera is OFF by default)
        self._cam_body_h = 264
        self._cam_body.setMaximumHeight(0)
        self._cam_body.setVisible(False)

        cam_lay.addWidget(self._cam_body)

        lay.addWidget(cam_card)

        # ── 5. Gesture Commands ───────────────────────────────────────────
        lib_title = QLabel("GESTURE COMMANDS")
        lib_title.setStyleSheet(
            f"color: {config.COLOR_MUTED}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1px; margin-top: 4px;"
        )
        lay.addWidget(lib_title)
        self._build_gesture_grid(lay)

        lay.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ── Gesture grid ──────────────────────────────────────────────────────
    def _build_gesture_grid(self, parent_lay: QVBoxLayout) -> None:
        from services.mission_generator import MissionGenerator
        gestures = MissionGenerator.all_gesture_info()
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, g in enumerate(gestures):
            card = GestureCard(g["gesture_name"], g["icon_path"])
            card.clicked.connect(self.manual_gesture_added.emit)
            grid.addWidget(card, i // 3, i % 3)
        parent_lay.addLayout(grid)

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _make_card() -> QFrame:
        f = QFrame()
        f.setObjectName("aiCard")
        f.setStyleSheet(f"""
            QFrame#aiCard {{
                background: {config.COLOR_CARD};
                border: 1px solid {config.COLOR_BORDER};
                border-radius: 12px;
            }}
        """)
        return f

    @staticmethod
    def _btn_style(color: str, small: bool = False) -> str:
        fs = 10 if small else 11
        return f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {color};
                border-radius: 6px;
                color: {color};
                font-size: {fs}px;
                font-weight: 600;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background: {color}22;
            }}
            QPushButton:checked {{
                background: {config.COLOR_DANGER}22;
                border-color: {config.COLOR_DANGER};
                color: {config.COLOR_DANGER};
            }}
        """

    # ── Slots ──────────────────────────────────────────────────
    def _on_camera_toggled(self, checked: bool) -> None:
        self._camera_on = checked
        if checked:
            self._cam_btn.setText("Camera OFF")
            self._cam_status.setStyleSheet(f"color: {config.COLOR_SUCCESS}; font-size: 12px;")
            self._cam_status.setText("● Camera Feed")
            self._expand_camera()
        else:
            self._cam_btn.setText("Camera ON")
            self._cam_status.setStyleSheet(f"color: {config.COLOR_MUTED}; font-size: 12px;")
            self.camera_widget.clear_frame()
            self._collapse_camera()
        self.camera_toggle_requested.emit(checked)

    def _expand_camera(self) -> None:
        """Animate camera body open."""
        if self._cam_body is None:
            return
        # Stop any running animation
        if self._cam_anim and self._cam_anim.state() == QPropertyAnimation.State.Running:
            self._cam_anim.stop()

        self._cam_body.setVisible(True)
        self._cam_body.setMaximumHeight(0)

        self._cam_anim = QPropertyAnimation(self._cam_body, b"maximumHeight", self)
        self._cam_anim.setDuration(260)
        self._cam_anim.setStartValue(0)
        self._cam_anim.setEndValue(self._cam_body_h + 20)  # small extra so widget breathes
        self._cam_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._cam_anim.start()

    def _collapse_camera(self) -> None:
        """Animate camera body closed."""
        if self._cam_body is None:
            return
        if self._cam_anim and self._cam_anim.state() == QPropertyAnimation.State.Running:
            self._cam_anim.stop()

        self._cam_anim = QPropertyAnimation(self._cam_body, b"maximumHeight", self)
        self._cam_anim.setDuration(220)
        self._cam_anim.setStartValue(self._cam_body.height())
        self._cam_anim.setEndValue(0)
        self._cam_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._cam_anim.finished.connect(lambda: self._cam_body.setVisible(False))
        self._cam_anim.start()

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Gesture Model", config.DEFAULT_MODEL_PATH,
            "Pickle Files (*.pkl);;All Files (*.*)"
        )
        if path:
            self._model_path_lbl.setText(os.path.basename(path))
            self._model_path_lbl.setToolTip(path)
            self.model_path_changed.emit(path)

    # ── Public update API ─────────────────────────────────────────────────
    def update_camera_frame(self, bgr: np.ndarray) -> None:
        self.camera_widget.update_frame(bgr)

    def update_progress(self, pct: int) -> None:
        cw = self.camera_widget
        cw._prog_bar.setValue(pct)
        if not cw._confirmed:
            cw._prog_lbl.setText(f"{cw._current_gesture} ({pct}%)")
            if not cw._prog_overlay.isVisible():
                cw._prog_overlay.show()

    def update_current_gesture(self, name: str) -> None:
        cw = self.camera_widget
        cw._current_gesture = name
        cw._confirmed = False
        cw._prog_lbl.setText(f"{name} (0%)")
        cw._prog_bar.setValue(0)
        cw._prog_overlay.show()

    def on_gesture_confirmed(self, name: str) -> None:
        cw = self.camera_widget
        cw._current_gesture = name
        cw._confirmed = True
        cw._prog_lbl.setText(f"✓ {name}")
        cw._prog_bar.setValue(100)
        cw._prog_overlay.show()
        QTimer.singleShot(1200, self._clear_confirmation)

    def _clear_confirmation(self) -> None:
        cw = self.camera_widget
        cw._confirmed = False
        cw._current_gesture = ""
        cw._prog_overlay.hide()

    def update_quality(self, metrics: dict) -> None:
        """Route quality metrics to the camera widget overlay (no separate card)."""
        self.camera_widget.update_quality_overlay(metrics)

    def on_model_status(self, ok: bool, msg: str) -> None:
        color = config.COLOR_SUCCESS if ok else config.COLOR_DANGER
        self._model_path_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._model_path_lbl.setToolTip(msg)
