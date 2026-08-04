import os
import cv2
import numpy as np
import joblib
import time
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class GestureTesterApp:
    def __init__(self, model_dir=None, app_dir=None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = model_dir if model_dir else os.path.join(script_dir, "models")
        self.app_dir = app_dir if app_dir else script_dir
        self.model = None
        self.scaler = None
        self.classes = []
        
        # Paths
        self.model_path = os.path.join(self.model_dir, "gesture_model.pkl")
        self.scaler_path = os.path.join(self.model_dir, "scaler.pkl")
        self.task_path = os.path.join(self.app_dir, "hand_landmarker.task")
        
        # Ensure directories exist
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.app_dir, exist_ok=True)
        
        # MediaPipe Tasks API Setup
        self._ensure_detector_model_exists()
        
        base_options = python.BaseOptions(model_asset_path=self.task_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

        # Hand skeleton connections layout (to draw without mp.solutions)
        self.connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),      # Index finger
            (5, 9), (9, 10), (10, 11), (11, 12),  # Middle finger
            (9, 13), (13, 14), (14, 15), (15, 16),# Ring finger
            (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
            (0, 17),                             # Wrist to pinky base
            (5, 9), (9, 13), (13, 17)            # Horizontal base line joints
        ]

    def _ensure_detector_model_exists(self):
        """
        Downloads Google's MediaPipe Hand Landmarker model file if it is not present.
        """
        if not os.path.exists(self.task_path):
            print("Downloading hand_landmarker.task model (approx. 5.6 MB)...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            try:
                urllib.request.urlretrieve(url, self.task_path)
                print("Model file downloaded successfully.")
            except Exception as e:
                print(f"Error downloading landmarker model: {e}")
                raise e

    def load_model(self):
        """
        Loads the trained classification model and scaler files.
        """
        # Check both root and nested folder paths
        if not os.path.exists(self.model_path):
            alt_model_path = os.path.join("AIGestureModelTrainer", "models", "gesture_model.pkl")
            alt_scaler_path = os.path.join("AIGestureModelTrainer", "models", "scaler.pkl")
            if os.path.exists(alt_model_path):
                self.model_path = alt_model_path
                self.scaler_path = alt_scaler_path
                print(f"Fallback: Found model at alt path: {self.model_path}")
            else:
                return False, f"Classifier model file not found at '{self.model_path}' or '{alt_model_path}'. Please run the trainer GUI first."

        try:
            self.model = joblib.load(self.model_path)
            print("Model loaded successfully.")
            
            # Load scaler if it exists
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
                print("StandardScaler loaded successfully.")
            else:
                self.scaler = None
                print("No scaler required.")
                
            # Read classes
            if hasattr(self.model, "classes_"):
                self.classes = list(self.model.classes_)
                print(f"Classes: {self.classes}")
            else:
                self.classes = ["Backward", "Down", "Forward", "Hover", "Land", "Left", "Right", "Takeoff", "Up"]
                print(f"Using default fallback classes list: {self.classes}")
                
            return True, "Model loaded successfully."
        except Exception as e:
            return False, f"Failed to load model: {str(e)}"

    def normalize_landmarks(self, hand_landmarks):
        """
        Translates wrist to origin and scales landmarks by Wrist -> Middle finger MCP distance.
        """
        wrist = hand_landmarks[0]
        x0, y0, z0 = wrist.x, wrist.y, wrist.z
        
        # 1. Translate Wrist to origin (0, 0, 0)
        rel_coords = []
        for lm in hand_landmarks:
            rel_coords.append([lm.x - x0, lm.y - y0, lm.z - z0])
            
        rel_coords = np.array(rel_coords)
        
        # 2. Scale relative to Wrist -> Middle finger MCP (landmark 9)
        middle_mcp_rel = rel_coords[9]
        scale_factor = np.sqrt(np.sum(middle_mcp_rel**2))
        
        if scale_factor == 0:
            scale_factor = 1e-6
            
        norm_coords = rel_coords / scale_factor
        
        # 3. Flatten to 63 features
        return norm_coords.flatten().tolist()

    def draw_skeleton(self, frame, hand_landmarks):
        """
        Draws custom hand coordinates skeletal lines and joint circles.
        """
        h, w, _ = frame.shape
        points = []
        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            points.append((cx, cy))

        # Draw connection lines
        for conn in self.connections:
            pt1 = points[conn[0]]
            pt2 = points[conn[1]]
            cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        # Draw joint nodes
        for idx, pt in enumerate(points):
            if idx in [0, 5, 9, 13, 17]:
                cv2.circle(frame, pt, 6, (0, 255, 0), -1)
                cv2.circle(frame, pt, 3, (255, 255, 255), -1)
            else:
                cv2.circle(frame, pt, 4, (0, 255, 0), -1)
                cv2.circle(frame, pt, 2, (255, 255, 255), -1)

    def run(self):
        # 1. Load trained classifier
        success, msg = self.load_model()
        if not success:
            print(f"CRITICAL ERROR: {msg}")
            return

        # 2. Start Camera Capture
        print("Starting camera stream...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("CRITICAL ERROR: Cannot open webcam.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("\n=== Real-time Gesture Control Tester ===")
        print("Hold your hand inside the webcam field of view.")
        print("Press ESC or 'q' key to quit.")

        prev_time = time.time()
        fps = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror frame for intuitive selfie view
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert NumPy array to MediaPipe Image object
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = self.detector.detect(mp_image)

            gesture_name = "No Hand Detected"
            confidence = 0.0
            hand_box = None

            if results.hand_landmarks and len(results.hand_landmarks) > 0:
                # Process the first detected hand
                landmarks_list = results.hand_landmarks[0]
                
                # Draw hand skeleton overlay
                self.draw_skeleton(frame, landmarks_list)

                # Compute hand bounding box
                x_coords = [int(lm.x * w) for lm in landmarks_list]
                y_coords = [int(lm.y * h) for lm in landmarks_list]
                hand_box = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

                # Normalize features (63-dimensional coordinate vectors)
                features = self.normalize_landmarks(landmarks_list)
                X = np.array([features])

                # Transform features using StandardScaler if it exists
                if self.scaler is not None:
                    X = self.scaler.transform(X)

                # Classify hand gesture
                try:
                    prediction = self.model.predict(X)[0]
                    gesture_name = str(prediction)

                    # Extract classification probability
                    if hasattr(self.model, "predict_proba"):
                        probs = self.model.predict_proba(X)[0]
                        class_idx = list(self.model.classes_).index(prediction)
                        confidence = probs[class_idx] * 100
                    else:
                        confidence = 100.0
                except Exception as e:
                    gesture_name = f"Error: {str(e)[:15]}"

            # Calculate FPS
            curr_time = time.time()
            fps = 0.9 * fps + 0.1 / (curr_time - prev_time)
            prev_time = curr_time

            # --- Visual HUD Overlay ---
            # 1. Top status bar background
            cv2.rectangle(frame, (0, 0), (w, 55), (18, 18, 18), -1)
            cv2.line(frame, (0, 55), (w, 55), (255, 229, 0), 1)

            # 2. Header text overlays
            cv2.putText(frame, "AI DRONE GESTURE TESTER (Tasks API)", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 229, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, f"FPS: {fps:.1f}", (w - 100, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
            
            # Model algorithm detail
            model_info = f"Classifier: {type(self.model).__name__} | Scaler: {'Fitted' if self.scaler else 'None'}"
            cv2.putText(frame, model_info, (15, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)

            # 3. Target lock box and floating label
            if hand_box is not None:
                x_min, y_min, x_max, y_max = hand_box
                
                # Dynamic HUD targeting frame
                color = (0, 255, 204) if confidence > 80 else (0, 128, 255)
                cv2.rectangle(frame, (x_min - 15, y_min - 15), (x_max + 15, y_max + 15), color, 1)
                
                # Floating Label
                label = f"{gesture_name} ({confidence:.1f}%)"
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                
                # Label BG box
                cv2.rectangle(frame, (x_min - 15, y_min - 35), (x_min - 15 + text_w + 10, y_min - 15), (18, 18, 18), -1)
                cv2.putText(frame, label, (x_min - 10, y_min - 21), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2, cv2.LINE_AA)

                # Print status
                cv2.putText(frame, f"Gesture: {gesture_name}", (15, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 204), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "No hand detected", (15, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2, cv2.LINE_AA)

            # Display Frame
            cv2.imshow("AI Gesture Model Tester", frame)

            # Keyboard triggers
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):
                break

        # Release resources
        cap.release()
        self.detector.close()
        cv2.destroyAllWindows()
        print("Camera released. Application terminated safely.")

if __name__ == "__main__":
    app = GestureTesterApp()
    app.run()
