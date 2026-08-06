import cv2
import numpy as np
import time
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class CameraThread(QThread):
    # Signals
    frame_updated = Signal(np.ndarray)  # Emits raw OpenCV BGR frame
    fps_updated = Signal(float)         # Emits camera FPS

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._run_flag = True
        self.is_simulated = False
        self.cap = None
        self.measured_fps = 30.0

    def run(self):
        self._run_flag = True
        self.cap = cv2.VideoCapture(self.camera_index)
        
        # Test if camera opens successfully
        if not self.cap.isOpened():
            print(f"Warning: Camera {self.camera_index} not found. Running in simulation mode.")
            self.is_simulated = True
        else:
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.is_simulated = False

        prev_time = time.time()
        fps = 0.0
        
        # Simulation parameters
        sim_time = 0.0
        
        while self._run_flag:
            start_loop = time.time()
            
            if not self.is_simulated:
                ret, frame = self.cap.read()
                if not ret:
                    # Capture failed, transition to simulation
                    self.is_simulated = True
                    continue
                # Mirror frame
                frame = cv2.flip(frame, 1)
            else:
                # Generate a premium dark grid background for simulation
                h, w = 480, 640
                frame = np.zeros((h, w, 3), dtype=np.uint8)
                
                # Dark cyan/navy ambient gradient background
                for y in range(h):
                    gradient_val = int(12 + 10 * np.sin(y / 100.0))
                    frame[y, :] = (gradient_val + 5, gradient_val, gradient_val // 2)
                
                # Draw grid lines
                grid_color = (30, 32, 48)
                for x in range(0, w, 40):
                    cv2.line(frame, (x, 0), (x, h), grid_color, 1)
                for y in range(0, h, 40):
                    cv2.line(frame, (0, y), (w, y), grid_color, 1)

                # Simulated camera UI decoration
                cv2.putText(frame, "SIMULATED FEED (No Camera)", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1, cv2.LINE_AA)
                
                # Draw scanning line
                scan_y = int((time.time() * 100) % h)
                cv2.line(frame, (0, scan_y), (w, scan_y), (124, 77, 255, 30), 1)
                
                # Simulate a hand coordinate moving in a circle
                sim_time += 0.03
                hand_x = int(w / 2 + 120 * np.cos(sim_time))
                hand_y = int(h / 2 + 80 * np.sin(sim_time))
                
                # Only draw "detected hand" every few seconds to show fluctuations
                cycle = int(sim_time) % 15
                if cycle < 10:  # Hand present
                    # Draw a mock bounding box
                    box_w, box_h = 160, 180
                    x1 = hand_x - box_w // 2
                    y1 = hand_y - box_h // 2
                    x2 = hand_x + box_w // 2
                    y2 = hand_y + box_h // 2
                    
                    # Draw mock skeleton connections
                    connections = [
                        (hand_x, hand_y + 60), (hand_x, hand_y), # Palm
                        (hand_x, hand_y), (hand_x - 40, hand_y - 20), # Thumb
                        (hand_x, hand_y), (hand_x - 20, hand_y - 50), # Index
                        (hand_x, hand_y), (hand_x, hand_y - 60),      # Middle
                        (hand_x, hand_y), (hand_x + 20, hand_y - 50), # Ring
                        (hand_x, hand_y), (hand_x + 40, hand_y - 30)  # Pinky
                    ]
                    for conn in connections:
                        cv2.circle(frame, conn, 5, (0, 230, 118), -1)
                    
                    # Joint connectors
                    cv2.line(frame, (hand_x, hand_y + 60), (hand_x, hand_y), (0, 230, 118), 2)
                    cv2.line(frame, (hand_x, hand_y), (hand_x - 40, hand_y - 20), (0, 230, 118), 2)
                    cv2.line(frame, (hand_x, hand_y), (hand_x - 20, hand_y - 50), (0, 230, 118), 2)
                    cv2.line(frame, (hand_x, hand_y), (hand_x, hand_y - 60), (0, 230, 118), 2)
                    cv2.line(frame, (hand_x, hand_y), (hand_x + 20, hand_y - 50), (0, 230, 118), 2)
                    cv2.line(frame, (hand_x, hand_y), (hand_x + 40, hand_y - 30), (0, 230, 118), 2)
                    
                    cv2.circle(frame, (hand_x, hand_y), 8, (124, 77, 255), -1)
                else:
                    # Draw user-friendly placeholder message when no hand is present
                    msg = "Place your hand inside the frame"
                    (tw, th), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    cv2.putText(frame, msg, (int((w - tw)/2), int((h - th)/2)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (142, 148, 178), 1, cv2.LINE_AA)

            # Measure frame rate
            curr_time = time.time()
            fps = 0.9 * fps + 0.1 / max((curr_time - prev_time), 1e-6)
            prev_time = curr_time
            self.measured_fps = fps
            
            # Emit frames and stats
            self.frame_updated.emit(frame)
            self.fps_updated.emit(fps)

            # Cap frame rate at 30 FPS to reduce CPU consumption
            elapsed = time.time() - start_loop
            sleep_time = max(1.0 / 30.0 - elapsed, 0)
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Cleanup
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def stop(self):
        self._run_flag = False
        self.wait()
