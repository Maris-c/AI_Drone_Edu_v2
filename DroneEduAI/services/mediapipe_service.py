"""
MediaPipeService — background QThread that drives the camera loop.

Architecture (v3 — decoupled inference):
  ┌─ QThread (MediaPipeService.run) ──────────────────────────┐
  │  Camera read → flip → emit frame_ready → submit to infer  │
  │  Quality metrics every N frames (cheap, stays here)        │
  └───────────────────────────────────────────────────────────┘
                          │ latest frame (lock-protected)
                          ▼
  ┌─ threading.Thread (_InferenceWorker) ─────────────────────┐
  │  Downscale → cvtColor → MediaPipe → GestureClassifier     │
  │  Emits: gesture_detected, stores landmarks back            │
  └───────────────────────────────────────────────────────────┘

Key wins vs v2:
  • Camera loop NEVER blocks on MediaPipe → display FPS ≈ camera FPS (30)
  • MediaPipe runs on a 0.5× downscaled frame → ~4× cheaper per inference
  • Inference always uses the *latest* frame, never a stale one
  • FPS cap (DISPLAY_FPS_CAP) prevents wasting CPU above monitor refresh rate
  • Quality metrics use the cheap gray buffer computed in the camera thread
"""
from __future__ import annotations
import os
import time
import threading
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

_ACCENT_BGR   = (246, 92, 139)
_ACCENT_WHITE = (252, 250, 248)

# How often to recompute quality metrics (relative to display frames)
_QUALITY_EVERY_N = 4

# Minimum seconds between frame submissions to the inference thread.
# This prevents the inference thread from being overwhelmed and ensures
# it always works on the freshest available frame.
_MIN_INFER_INTERVAL = 0.05   # ~20 fps max inference rate


# ── Inference worker (plain threading.Thread, not QThread) ───────────────────

class _InferenceWorker(threading.Thread):
    """
    Runs MediaPipe + classifier on a shared 'latest frame' slot.

    The camera thread submits frames via submit(); the worker always picks up
    the most-recent frame, discarding stale ones automatically.
    """

    def __init__(self, detector: mp_vision.HandLandmarker,
                 classifier: GestureClassifier,
                 service: "MediaPipeService"):
        super().__init__(daemon=True, name="InferenceWorker")
        self._detector    = detector
        self._classifier  = classifier
        self._svc         = service

        self._lock        = threading.Lock()
        self._event       = threading.Event()
        self._latest_frame: Optional[np.ndarray] = None
        self._active      = True

        # Inference scale factor (frame submitted is already at this scale)
        self._scale = config.INFER_SCALE if config.INFER_SCALE != 1.0 else 1.0

    def submit(self, frame: np.ndarray) -> None:
        """Non-blocking: store the latest frame and wake the worker."""
        with self._lock:
            self._latest_frame = frame   # caller already made a copy
        self._event.set()

    def stop(self) -> None:
        self._active = False
        self._event.set()

    def run(self) -> None:
        last_gesture = "No Hand"
        last_conf    = 0.0
        while self._active:
            triggered = self._event.wait(timeout=0.5)
            self._event.clear()
            if not self._active:
                break
            if not triggered:
                continue

            with self._lock:
                frame = self._latest_frame
                self._latest_frame = None
            if frame is None:
                continue

            # ── Inference on downscaled frame ─────────────────────────
            h, w = frame.shape[:2]

            # Downscale for MediaPipe (keeps full-res for drawing)
            if self._scale != 1.0:
                small_w = max(int(w * self._scale), 64)
                small_h = max(int(h * self._scale), 48)
                small   = cv2.resize(frame, (small_w, small_h),
                                     interpolation=cv2.INTER_LINEAR)
            else:
                small = frame

            rgb    = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            try:
                results = self._detector.detect(mp_img)
            except Exception:
                continue

            if results.hand_landmarks:
                lm = results.hand_landmarks[0]
                # Write shared state under lock
                with self._svc._result_lock:
                    self._svc._last_landmarks = lm
                    self._svc._has_hand       = True

                g, c = self._classifier.predict(lm)
                if g != last_gesture or abs(c - last_conf) > 1.0:
                    last_gesture = g
                    last_conf    = c
                    with self._svc._result_lock:
                        self._svc._last_gesture = g
                        self._svc._last_conf    = c
                    self._svc.gesture_detected.emit(g, c)
            else:
                had_hand = False
                with self._svc._result_lock:
                    had_hand = self._svc._has_hand
                    self._svc._last_landmarks = None
                    self._svc._has_hand       = False
                    self._svc._last_gesture   = "No Hand"
                    self._svc._last_conf      = 0.0
                if had_hand:
                    last_gesture = "No Hand"
                    last_conf    = 0.0
                    self._svc.gesture_detected.emit("No Hand", 0.0)


# ── Main service ──────────────────────────────────────────────────────────────

class MediaPipeService(QThread):
    """
    QThread owning the camera capture loop.
    MediaPipe inference is offloaded to _InferenceWorker.
    """

    frame_ready      = Signal(object)        # np.ndarray BGR
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

        self.task_path   = config.DEFAULT_TASK_PATH
        self.model_path  = config.DEFAULT_MODEL_PATH
        self.scaler_path = config.DEFAULT_SCALER_PATH

        # Shared inference state — written by _InferenceWorker, read by camera loop
        self._result_lock    = threading.Lock()
        self._last_landmarks = None
        self._has_hand       = False
        self._last_gesture   = "No Hand"
        self._last_conf      = 0.0
        self._last_quality: dict = {}

    # ------------------------------------------------------------------
    def start_service(self) -> None:
        self._running = True
        self.start()

    def stop_service(self) -> None:
        self._running = False
        self.wait(4000)

    def update_model_path(self, model_path: str) -> None:
        self.model_path  = model_path
        scaler_guess     = os.path.join(os.path.dirname(model_path), "scaler.pkl")
        self.scaler_path = scaler_guess
        ok, msg = self.classifier.load(model_path, scaler_guess)
        self.model_status.emit(ok, msg)

    # ------------------------------------------------------------------
    def run(self) -> None:
        # 1. Load classifier
        ok, msg = self.classifier.load(self.model_path, self.scaler_path)
        self.model_status.emit(ok, msg)

        # 2. Init MediaPipe detector
        if not self._init_detector():
            return

        # 3. Open camera — try MJPEG first (unlocks 30fps on most webcams)
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.model_status.emit(False, "Cannot open camera (index 0).")
            return

        # MJPEG: dramatically reduces USB bandwidth → allows 30fps at 640×480
        # where uncompressed YUY2 would cap at 15fps on most USB 2.0 webcams
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, 30)        # explicit FPS request
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimise latency (1 frame buffer)

        # 4. Start inference worker thread
        worker = _InferenceWorker(self.detector, self.classifier, self)
        worker.start()

        self._prev_time    = time.time()
        frame_count        = 0
        last_infer_time    = 0.0
        gray_small: Optional[np.ndarray] = None   # reused small gray buffer

        # Separate raw camera FPS tracker (measures cap.read() rate)
        self._cam_fps    = 0.0
        self._cam_prev   = time.time()

        # 5. Camera loop (never blocks on inference)
        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.005)
                continue

            now = time.time()

            # Raw camera FPS (unthrottled)
            cam_dt         = max(now - self._cam_prev, 1e-6)
            self._cam_fps  = 0.9 * self._cam_fps + 0.1 / cam_dt
            self._cam_prev = now

            frame_count += 1
            cv2.flip(frame, 1, dst=frame)    # in-place
            h, w = frame.shape[:2]

            # Display FPS (measured after processing, represents true output rate)
            dt          = max(now - self._prev_time, 1e-6)
            self._fps   = 0.85 * self._fps + 0.15 / dt
            self._prev_time = now

            # Submit to inference thread (throttled, non-blocking)
            if now - last_infer_time >= _MIN_INFER_INTERVAL:
                worker.submit(frame.copy())
                last_infer_time = now

            # Draw skeleton from last inference result (snapshot under lock)
            with self._result_lock:
                lm_snap  = self._last_landmarks
                has_hand = self._has_hand

            if has_hand and lm_snap is not None:
                self._draw_skeleton(frame, lm_snap, w, h)

            # Quality metrics — computed on a DOWNSCALED gray (cheap!)
            if frame_count % _QUALITY_EVERY_N == 0:
                sw = max(w >> 1, 64)    # half width
                sh = max(h >> 1, 48)    # half height
                small = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_NEAREST)
                gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY, dst=gray_small)
                with self._result_lock:
                    lm_q   = self._last_landmarks
                    conf_q = self._last_conf
                q = self._compute_quality(gray_small, lm_q, w, h, conf_q)
                self._last_quality = q
                self.quality_updated.emit(q)

            # Emit display frame (QImage.Format_BGR888 — no cvtColor needed in UI)
            display = frame if frame.flags["C_CONTIGUOUS"] else np.ascontiguousarray(frame)
            self.frame_ready.emit(display)

        # Shutdown
        worker.stop()
        worker.join(3.0)
        cap.release()
        if self.detector:
            self.detector.close()

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
            opts      = mp_vision.HandLandmarkerOptions(
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
            cv2.line(frame, pts[a], pts[b], _ACCENT_BGR, 1)
        key_ids = {0, 5, 9, 13, 17}
        for i, pt in enumerate(pts):
            r = 5 if i in key_ids else 3
            cv2.circle(frame, pt, r, _ACCENT_BGR,   -1)
            cv2.circle(frame, pt, r - 1, _ACCENT_WHITE, -1)

    def _compute_quality(
        self, gray: np.ndarray, landmarks, w: int, h: int, conf: float
    ) -> dict:
        brightness = float(gray.mean())
        blur_score = float(cv2.Laplacian(gray, cv2.CV_32F).var())

        hand_ok = landmarks is not None
        roi_ok  = False
        if hand_ok:
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            roi_ok = (
                min(xs) >= 0.05 and max(xs) <= 0.95
                and min(ys) >= 0.05 and max(ys) <= 0.95
            )

        def _level(val, lo_bad, lo_warn, hi_warn, hi_bad):
            if val < lo_bad  or val > hi_bad:  return "error"
            if val < lo_warn or val > hi_warn: return "warning"
            return "good"

        fps     = self._fps
        cam_fps = getattr(self, "_cam_fps", fps)

        return {
            "Brightness":     {
                "value":  f"{brightness:.0f}",
                "status": _level(brightness, 30, 60, 210, 240),
            },
            "Blur":           {
                "value":  f"{blur_score:.0f}",
                "status": "good" if blur_score > 70 else (
                    "warning" if blur_score > 35 else "error"),
            },
            "Hand Detection": {
                "value":  "Detected" if hand_ok else "None",
                "status": "good" if hand_ok else "error",
            },
            "ROI Validation": {
                "value":  "Inside" if roi_ok else ("Outside" if hand_ok else "—"),
                "status": "good" if roi_ok else ("warning" if hand_ok else "error"),
            },
            "FPS":            {
                "value":  f"{fps:.0f}",
                "status": "good" if fps >= 20 else ("warning" if fps >= 12 else "error"),
            },
            "Confidence":     {
                "value":  f"{conf:.1f}%",
                "status": "good" if conf > 75 else ("warning" if conf > 50 else "error"),
            },
        }
