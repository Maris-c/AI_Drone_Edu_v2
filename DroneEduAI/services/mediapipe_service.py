"""
MediaPipeService — background QThread that drives the camera loop.

Responsibilities:
  • OpenCV camera capture
  • MediaPipe Tasks Hand Landmarker inference
  • GestureClassifier prediction
  • Quality metric computation
  • Emitting Qt signals to the main thread

All heavy work is in run().  The UI thread only reads emitted signals.
"""
from __future__ import annotations
import os
import time
from typing import Optional

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from PySide6.QtCore import QThread, Signal

import config
from .gesture_classifier import GestureClassifier

# Hand skeleton connection pairs (landmark indices)
_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17), (5, 9), (9, 13), (13, 17),
]

_ACCENT_BGR   = (246, 92, 139)   # #8B5CF6 in BGR
_ACCENT_WHITE = (252, 250, 248)  # #F8FAFC in BGR


class MediaPipeService(QThread):
    # -----------------------------------------------------------------
    # Signals (emitted from worker thread, received in main thread)
    # -----------------------------------------------------------------
    frame_ready      = Signal(object)        # np.ndarray BGR copy
    gesture_detected = Signal(str, float)    # gesture_name, confidence%
    quality_updated  = Signal(dict)          # quality metrics dict
    model_status     = Signal(bool, str)     # loaded_ok, message

    def __init__(self, camera_index: int = config.DEFAULT_CAMERA_INDEX, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running     = False
        self._fps         = 0.0
        self._prev_time   = time.time()

        self.classifier = GestureClassifier()
        self.detector: Optional[mp_vision.HandLandmarker] = None

        # Paths (can be updated before start)
        self.task_path   = config.DEFAULT_TASK_PATH
        self.model_path  = config.DEFAULT_MODEL_PATH
        self.scaler_path = config.DEFAULT_SCALER_PATH

    # ------------------------------------------------------------------
    # Public control API (called from main thread)
    # ------------------------------------------------------------------
    def start_service(self) -> None:
        self._running = True
        self.start()

    def stop_service(self) -> None:
        self._running = False
        self.wait(3000)

    def update_model_path(self, model_path: str) -> None:
        """Hot-reload the classifier while the thread is running."""
        self.model_path  = model_path
        scaler_guess     = os.path.join(os.path.dirname(model_path), "scaler.pkl")
        self.scaler_path = scaler_guess
        # Reload in worker thread context or directly if thread is idle
        ok, msg = self.classifier.load(model_path, scaler_guess)
        self.model_status.emit(ok, msg)

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        # 1. Load classifier
        ok, msg = self.classifier.load(self.model_path, self.scaler_path)
        self.model_status.emit(ok, msg)

        # 2. Init MediaPipe
        if not self._init_detector():
            return

        # 3. Open camera (optimized for Windows using DirectShow for faster startup)
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.model_status.emit(False, "Cannot open camera (index 0).")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self._prev_time = time.time()

        # 4. Main loop
        while self._running:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            # MediaPipe inference
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            results = self.detector.detect(mp_img)

            # FPS
            now = time.time()
            dt = max(now - self._prev_time, 1e-6)
            self._fps = 0.9 * self._fps + 0.1 / dt
            self._prev_time = now

            landmarks = None
            gesture   = "No Hand"
            conf      = 0.0

            if results.hand_landmarks:
                landmarks = results.hand_landmarks[0]
                self._draw_skeleton(frame, landmarks, w, h)
                gesture, conf = self.classifier.predict(landmarks)
                self.gesture_detected.emit(gesture, conf)

            # Quality metrics
            quality = self._compute_quality(frame, landmarks, w, h, conf)
            self.quality_updated.emit(quality)

            # Emit a copy so the UI thread owns the data
            self.frame_ready.emit(frame.copy())

        cap.release()
        if self.detector:
            self.detector.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _init_detector(self) -> bool:
        if not os.path.exists(self.task_path):
            self.model_status.emit(
                False,
                f"hand_landmarker.task not found:\n{self.task_path}\n"
                "Please check GestureTesterApp folder."
            )
            return False
        try:
            base_opts = mp_python.BaseOptions(model_asset_path=self.task_path)
            opts = mp_vision.HandLandmarkerOptions(
                base_options=base_opts,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_hands=1,
                min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.6,
            )
            self.detector = mp_vision.HandLandmarker.create_from_options(opts)
            return True
        except Exception as exc:
            self.model_status.emit(False, f"MediaPipe init failed: {exc}")
            return False

    def _draw_skeleton(self, frame, lm_list, w: int, h: int) -> None:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in lm_list]
        for a, b in _HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], _ACCENT_BGR, 2)
        for i, pt in enumerate(pts):
            r = 6 if i in (0, 5, 9, 13, 17) else 4
            cv2.circle(frame, pt, r, _ACCENT_BGR,   -1)
            cv2.circle(frame, pt, r - 2, _ACCENT_WHITE, -1)

    def _compute_quality(self, frame, landmarks, w: int, h: int, conf: float) -> dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        hand_ok = landmarks is not None

        # ROI check: hand fits in central 80% region
        roi_ok = False
        if hand_ok:
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            roi_ok = (min(xs) >= 0.05 and max(xs) <= 0.95
                      and min(ys) >= 0.05 and max(ys) <= 0.95)

        def _level(val, low_bad, low_warn, high_warn, high_bad):
            if val < low_bad or val > high_bad:   return "error"
            if val < low_warn or val > high_warn:  return "warning"
            return "good"

        return {
            "Brightness":     {"value": f"{brightness:.0f}", "status": _level(brightness, 30, 60, 210, 240)},
            "Blur":           {"value": f"{blur_score:.0f}", "status": "good" if blur_score > 70 else ("warning" if blur_score > 35 else "error")},
            "Hand Detection": {"value": "Detected" if hand_ok else "None", "status": "good" if hand_ok else "error"},
            "ROI Validation": {"value": "Inside" if roi_ok else ("Outside" if hand_ok else "—"),
                               "status": "good" if roi_ok else ("warning" if hand_ok else "error")},
            "FPS":            {"value": f"{self._fps:.1f}", "status": "good" if self._fps >= 20 else ("warning" if self._fps >= 10 else "error")},
            "Confidence":     {"value": f"{conf:.1f}%", "status": "good" if conf > 75 else ("warning" if conf > 50 else "error")},
        }
