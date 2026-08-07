import os
import time
import cv2
import joblib
import urllib.request
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class ModelTesterEngine:
    def __init__(self, model_path=None, scaler_path=None, task_path=None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.app_dir = script_dir
        self.model_path = model_path if model_path else os.path.join(script_dir, "models", "gesture_model.pkl")
        self.scaler_path = scaler_path if scaler_path else os.path.join(script_dir, "models", "scaler.pkl")
        self.task_path = task_path if task_path else os.path.join(script_dir, "hand_landmarker.task")
        
        self.model = None
        self.scaler = None
        self.classes = []
        self.detector = None
        
        # Hand skeleton connections layout for drawing
        self.connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),      # Index finger
            (5, 9), (9, 10), (10, 11), (11, 12),  # Middle finger
            (9, 13), (13, 14), (14, 15), (15, 16),# Ring finger
            (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
            (0, 17),                             # Wrist to pinky base
            (5, 9), (9, 13), (13, 17)            # Base joints
        ]
        
    def ensure_landmarker_exists(self):
        """Downloads MediaPipe HandLandmarker task if missing."""
        if not os.path.exists(self.task_path):
            os.makedirs(os.path.dirname(self.task_path), exist_ok=True)
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            print(f"Downloading MediaPipe HandLandmarker model to {self.task_path}...")
            urllib.request.urlretrieve(url, self.task_path)
            print("Landmarker model download complete.")

    def initialize_detector(self):
        """Initializes the MediaPipe Tasks HandLandmarker detector."""
        self.ensure_landmarker_exists()
        base_options = python.BaseOptions(model_asset_path=self.task_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def load_model(self, custom_model_path=None, custom_scaler_path=None):
        """Loads trained classification model (.pkl) and optional scaler (.pkl)."""
        if custom_model_path:
            self.model_path = custom_model_path
        if custom_scaler_path:
            self.scaler_path = custom_scaler_path

        if not os.path.exists(self.model_path):
            # Fallback check
            alt_path = os.path.join("AIGestureModelTrainer", "models", "gesture_model.pkl")
            if os.path.exists(alt_path):
                self.model_path = alt_path
                self.scaler_path = os.path.join("AIGestureModelTrainer", "models", "scaler.pkl")
            else:
                return False, f"Model file not found at '{self.model_path}'"

        try:
            self.model = joblib.load(self.model_path)
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
            else:
                self.scaler = None
                
            if hasattr(self.model, "classes_"):
                self.classes = [str(c) for c in self.model.classes_]
            else:
                self.classes = ["Backward", "Down", "Forward", "Hover", "Land", "Left", "Right", "Takeoff", "Up"]
                
            return True, f"Loaded model '{os.path.basename(self.model_path)}' with {len(self.classes)} classes."
        except Exception as e:
            return False, f"Failed to load model: {str(e)}"

    def normalize_landmarks(self, hand_landmarks):
        """Translates wrist to origin and scales by Wrist -> Middle MCP distance (63 features)."""
        wrist = hand_landmarks[0]
        x0, y0, z0 = wrist.x, wrist.y, wrist.z
        
        rel_coords = []
        for lm in hand_landmarks:
            rel_coords.append([lm.x - x0, lm.y - y0, lm.z - z0])
        rel_coords = np.array(rel_coords)
        
        middle_mcp_rel = rel_coords[9]
        scale_factor = np.sqrt(np.sum(middle_mcp_rel**2))
        if scale_factor == 0:
            scale_factor = 1e-6
            
        norm_coords = rel_coords / scale_factor
        return norm_coords.flatten().tolist()

    def process_frame(self, frame_bgr):
        """
        Processes a single BGR frame for webcam or image testing.
        Returns:
            processed_frame, gesture_name, confidence, landmarks_detected, latency_ms
        """
        if self.detector is None:
            self.initialize_detector()
            
        t0 = time.time()
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = self.detector.detect(mp_image)
        latency_ms = (time.time() - t0) * 1000.0

        gesture_name = "No Hand Detected"
        confidence = 0.0
        landmarks_detected = False
        annotated_frame = frame_bgr.copy()

        if results.hand_landmarks and len(results.hand_landmarks) > 0:
            landmarks_detected = True
            landmarks = results.hand_landmarks[0]
            
            # Draw skeleton
            self.draw_skeleton(annotated_frame, landmarks)
            
            # Feature extraction
            features = self.normalize_landmarks(landmarks)
            X = np.array([features])
            
            if self.scaler is not None:
                X = self.scaler.transform(X)
                
            if self.model is not None:
                try:
                    prediction = self.model.predict(X)[0]
                    gesture_name = str(prediction)
                    if hasattr(self.model, "predict_proba"):
                        probs = self.model.predict_proba(X)[0]
                        cls_idx = list(self.model.classes_).index(prediction)
                        confidence = float(probs[cls_idx] * 100.0)
                    else:
                        confidence = 100.0
                except Exception as e:
                    gesture_name = f"Error: {str(e)[:15]}"

        return annotated_frame, gesture_name, confidence, landmarks_detected, latency_ms

    def draw_skeleton(self, frame, hand_landmarks):
        """Draws hand skeletal lines and joints on a frame."""
        h, w, _ = frame.shape
        points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]

        for conn in self.connections:
            pt1 = points[conn[0]]
            pt2 = points[conn[1]]
            cv2.line(frame, pt1, pt2, (0, 255, 128), 2, cv2.LINE_AA)

        for idx, pt in enumerate(points):
            color = (0, 255, 255) if idx in [0, 5, 9, 13, 17] else (0, 200, 255)
            cv2.circle(frame, pt, 4, color, -1)

    def evaluate_dataset(self, dataset_path, progress_callback=None):
        """
        Evaluates model on either an image dataset folder (subfolders per class)
        or a CSV dataset file containing features/labels.
        """
        if self.model is None:
            success, msg = self.load_model()
            if not success:
                return False, msg, {}

        if self.detector is None:
            self.initialize_detector()

        y_true = []
        y_pred = []
        latencies = []
        detected_count = 0
        total_samples = 0

        # Case 1: CSV File
        if os.path.isfile(dataset_path) and dataset_path.endswith('.csv'):
            try:
                df = pd.read_csv(dataset_path, header=None)
                label_col_idx = 63 if df.shape[1] >= 64 else df.shape[1] - 1
                
                # Check for header
                header_mask = df.iloc[:, label_col_idx].astype(str).str.strip().str.lower() == 'label'
                if header_mask.any():
                    df = df[~header_mask].reset_index(drop=True)

                X_raw = df.iloc[:, :label_col_idx].values
                y_raw = df.iloc[:, label_col_idx].astype(str).values

                # Clean numeric features
                X_df = pd.DataFrame(X_raw)
                for col in X_df.columns:
                    X_df[col] = pd.to_numeric(X_df[col], errors='coerce')
                X = X_df.values
                X = np.nan_to_num(X, nan=0.0)

                total_samples = len(y_raw)
                detected_count = total_samples  # CSV features are pre-extracted landmarks

                if self.scaler is not None:
                    X_eval = self.scaler.transform(X)
                else:
                    X_eval = X

                t0 = time.time()
                preds = self.model.predict(X_eval)
                t_end = time.time()
                
                latencies = [((t_end - t0) / total_samples) * 1000.0] * total_samples
                y_true = y_raw.tolist()
                y_pred = [str(p) for p in preds]

            except Exception as e:
                return False, f"Failed to evaluate CSV dataset: {str(e)}", {}

        # Case 2: Image Directory Structure
        elif os.path.isdir(dataset_path):
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
            samples = []
            
            for root, dirs, files in os.walk(dataset_path):
                for file in files:
                    if file.lower().endswith(image_extensions):
                        rel_dir = os.path.relpath(root, dataset_path)
                        label = rel_dir if rel_dir != "." else "Unknown"
                        img_path = os.path.join(root, file)
                        samples.append((img_path, label))

            if not samples:
                return False, "No test images (.jpg, .png) found in the selected folder.", {}

            total_samples = len(samples)

            for idx, (img_path, label) in enumerate(samples):
                frame = cv2.imread(img_path)
                if frame is None:
                    continue

                _, pred_gesture, conf, detected, latency_ms = self.process_frame(frame)
                latencies.append(latency_ms)

                if detected:
                    detected_count += 1
                    y_true.append(label)
                    y_pred.append(pred_gesture)

                if progress_callback:
                    progress_callback(int(((idx + 1) / total_samples) * 100))

        else:
            return False, "Invalid dataset path specified.", {}

        if not y_true or not y_pred:
            return False, f"No hands were detected in any of the {total_samples} test images.", {}

        # Calculate metrics
        acc = float(accuracy_score(y_true, y_pred))
        prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='macro', zero_division=0)
        
        # Get unique target classes from true & pred labels
        unique_classes = sorted(list(set(y_true + y_pred)))
        cm = confusion_matrix(y_true, y_pred, labels=unique_classes)
        clf_report = classification_report(y_true, y_pred, zero_division=0)
        
        detection_rate = float((detected_count / total_samples) * 100.0) if total_samples > 0 else 0.0
        avg_latency = float(np.mean(latencies)) if latencies else 0.0
        fps = float(1000.0 / avg_latency) if avg_latency > 0 else 0.0

        rating_grade, rating_text, rating_color = self.assess_model_quality(acc, detection_rate, avg_latency)

        metrics = {
            "total_samples": total_samples,
            "detected_samples": detected_count,
            "detection_rate": detection_rate,
            "accuracy": acc,
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "avg_latency_ms": avg_latency,
            "fps": fps,
            "classes": unique_classes,
            "confusion_matrix": cm,
            "classification_report": clf_report,
            "rating_grade": rating_grade,
            "rating_text": rating_text,
            "rating_color": rating_color,
            "model_path": self.model_path,
            "model_name": type(self.model).__name__ if self.model else "Unknown"
        }

        return True, "Evaluation completed successfully.", metrics

    @staticmethod
    def assess_model_quality(accuracy, detection_rate, latency_ms):
        """
        Evaluates overall model quality rating.
        Score formula: 0.6 * accuracy + 0.3 * (detection_rate / 100) + 0.1 * latency_bonus
        """
        score = (accuracy * 60.0) + (detection_rate * 0.3)
        if latency_ms < 30.0:
            score += 10.0
        elif latency_ms < 60.0:
            score += 5.0

        if score >= 90.0:
            return "Excellent", "Model demonstrates very high accuracy and fast response time. Fully ready for real-time drone control.", "#10B981"
        elif score >= 80.0:
            return "Good", "Model performance is stable and reliable for standard drone flight operations.", "#3B82F6"
        elif score >= 70.0:
            return "Fair", "Model performance is acceptable but may occasionally confuse visually similar gestures.", "#F59E0B"
        else:
            return "Needs Improvement", "Low accuracy or hand detection rate. Recommend collecting more training data and retraining the model.", "#EF4444"
