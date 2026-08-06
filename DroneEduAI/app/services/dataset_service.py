import csv
import os
from PySide6.QtCore import QObject, Signal

class DatasetCollectorService(QObject):
    # Signals
    sample_recorded = Signal(str, int) # gesture_name, count

    def __init__(self):
        super().__init__()
        self.active_recording = False
        self.recorded_samples = 0
        self.current_gesture = ""

    def start_recording(self, gesture_name):
        """
        Begins saving hand landmarks to CSV.
        """
        self.current_gesture = gesture_name
        self.active_recording = True
        self.recorded_samples = 0
        print(f"DatasetCollector: Recording coordinates for gesture: {gesture_name}")

    def stop_recording(self):
        """
        Stops active landmark recording.
        """
        self.active_recording = False
        print(f"DatasetCollector: Stopped recording. Total logged samples: {self.recorded_samples}")
        return self.recorded_samples

    def record_sample(self, flat_landmarks, output_file):
        """
        Appends a 63-dimensional coordinate array along with labels to target CSV.
        """
        if not self.active_recording:
            return
            
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        file_exists = os.path.exists(output_file)
        
        try:
            with open(output_file, mode="a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    # Write header
                    header = [f"lm_{i}_{coord}" for i in range(21) for coord in ["x", "y", "z"]]
                    header.append("label")
                    writer.writerow(header)
                
                row = list(flat_landmarks)
                row.append(self.current_gesture)
                writer.writerow(row)
                
            self.recorded_samples += 1
            self.sample_recorded.emit(self.current_gesture, self.recorded_samples)
        except Exception as e:
            print(f"Error logging landmark sample: {e}")
