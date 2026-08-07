"""
GestureClassifier — wraps the trained sklearn model.
Provides normalize_landmarks() → predict() → (gesture_name, confidence%).
"""
from __future__ import annotations
import os
from typing import List, Optional, Tuple

import numpy as np
import joblib


class GestureClassifier:
    def __init__(self) -> None:
        self.model = None
        self.scaler = None
        self.classes: List[str] = []
        self.model_path: Optional[str] = None

    # ------------------------------------------------------------------
    def load(
        self,
        model_path: str,
        scaler_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Load the sklearn classifier and optional StandardScaler."""
        if not os.path.exists(model_path):
            return False, f"Model file not found:\n{model_path}"

        try:
            self.model = joblib.load(model_path)
            self.model_path = model_path

            # Try to load paired scaler
            if scaler_path and os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            else:
                # Guess scaler path = same directory
                guess = os.path.join(os.path.dirname(model_path), "scaler.pkl")
                self.scaler = joblib.load(guess) if os.path.exists(guess) else None

            if hasattr(self.model, "classes_"):
                self.classes = list(self.model.classes_)
            else:
                self.classes = [
                    "Backward", "Down", "Forward", "Hover",
                    "Land", "Left", "Right", "Takeoff", "Up",
                ]

            return True, f"Model loaded — {len(self.classes)} classes."
        except Exception as exc:
            return False, f"Failed to load model: {exc}"

    def is_loaded(self) -> bool:
        return self.model is not None

    # ------------------------------------------------------------------
    def normalize_landmarks(self, hand_landmarks) -> List[float]:
        """
        Wrist → origin translation, then scale by Wrist–MiddleMCP distance.
        Returns a flat 63-feature vector.
        """
        wrist = hand_landmarks[0]
        x0, y0, z0 = wrist.x, wrist.y, wrist.z

        rel = np.array([[lm.x - x0, lm.y - y0, lm.z - z0] for lm in hand_landmarks])
        scale = float(np.linalg.norm(rel[9]))  # landmark 9 = Middle MCP
        if scale < 1e-6:
            scale = 1e-6

        return (rel / scale).flatten().tolist()

    # ------------------------------------------------------------------
    def predict(self, hand_landmarks) -> Tuple[str, float]:
        """Return (gesture_name, confidence_percent)."""
        if not self.is_loaded():
            return "No Model", 0.0
        try:
            features = self.normalize_landmarks(hand_landmarks)
            X = np.array([features])

            if self.scaler is not None:
                X = self.scaler.transform(X)

            pred = self.model.predict(X)[0]
            name = str(pred)

            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(X)[0]
                idx = list(self.model.classes_).index(pred)
                confidence = float(probs[idx]) * 100.0
            else:
                confidence = 100.0

            return name, confidence
        except Exception:
            return "Error", 0.0
