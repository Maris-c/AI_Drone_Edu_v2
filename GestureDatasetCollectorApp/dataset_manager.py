import os
import csv
import numpy as np
import pandas as pd
import cv2
from datetime import datetime

class DatasetManager:
    """
    Quản lý lưu trữ bộ dữ liệu cử chỉ dưới dạng file CSV (chuẩn hóa landmark) và ảnh gốc (.jpg) tương ứng.
    Tự động quản lý theo Session_ID của từng phiên làm việc.
    """
    def __init__(self, folder_path="dataset", file_name="gesture_dataset.csv"):
        self.folder_path = folder_path
        self.file_path = os.path.join(folder_path, file_name)
        self.images_folder = os.path.join(folder_path, "images")
        
        # 1. Tạo Session ID duy nhất cho phiên thu thập hiện tại
        self.session_id = datetime.now().strftime("sess_%Y%m%d_%H%M%S")
        print(f"Initializing new dataset collection session. Session ID: {self.session_id}")

        # Đảm bảo các thư mục tồn tại
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
        if not os.path.exists(self.images_folder):
            os.makedirs(self.images_folder)
            
        self.headers = []
        for i in range(21):
            self.headers.extend([f"x{i}", f"y{i}", f"z{i}"])
        self.headers.extend(["label", "timestamp", "session_id"])
        
        # Tạo file CSV mới và ghi header nếu file chưa tồn tại
        if not os.path.exists(self.file_path):
            with open(self.file_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)
        
        # Thống kê mẫu đã thu thập
        self.gesture_counts = {}
        self._load_statistics()

    def _load_statistics(self):
        """Đọc file CSV để lấy thống kê số lượng mẫu của từng cử chỉ (tất cả các session)."""
        self.gesture_counts = {}
        if os.path.exists(self.file_path):
            try:
                df = pd.read_csv(self.file_path)
                if not df.empty and 'label' in df.columns:
                    counts = df['label'].value_counts().to_dict()
                    for label, count in counts.items():
                        self.gesture_counts[label] = int(count)
            except Exception as e:
                print(f"Error reading dataset CSV stats: {e}")

    def get_gesture_counts(self):
        """Trả về thống kê số lượng mẫu hiện tại của mỗi cử chỉ."""
        return self.gesture_counts

    def get_total_samples(self):
        """Trả về tổng số mẫu đã thu thập."""
        return sum(self.gesture_counts.values())

    def normalize_landmarks(self, hand_landmarks):
        """
        Chuẩn hóa landmark bàn tay:
        1. Sử dụng Wrist (landmark 0) làm gốc tọa độ.
        2. Chuẩn hóa theo khoảng cách từ Wrist (0) đến Middle MCP (9) để loại bỏ yếu tố xa gần.
        3. Lưu tọa độ tương đối.
        
        Trả về: list 63 phần tử [x0, y0, z0, ..., x20, y20, z20] đã chuẩn hóa.
        """
        # Landmark gốc: Wrist
        wrist = hand_landmarks[0]
        x0, y0, z0 = wrist.x, wrist.y, wrist.z
        
        # 1. Tính tọa độ tương đối bằng cách dịch chuyển Wrist về gốc tọa độ (0,0,0)
        rel_coords = []
        for lm in hand_landmarks:
            rel_coords.append([lm.x - x0, lm.y - y0, lm.z - z0])
            
        rel_coords = np.array(rel_coords) # Shape: (21, 3)
        
        # 2. Tính khoảng cách Wrist -> Middle MCP (tọa độ tương đối của landmark 9)
        # Landmark 9 sau khi dịch chuyển có tọa độ là rel_coords[9]
        middle_mcp_rel = rel_coords[9]
        scale_factor = np.sqrt(np.sum(middle_mcp_rel**2))
        
        if scale_factor == 0:
            scale_factor = 1e-6 # Tránh chia cho 0
            
        # 3. Chia tất cả tọa độ tương đối cho khoảng cách scale_factor để chuẩn hóa kích thước
        norm_coords = rel_coords / scale_factor
        
        # Trải phẳng mảng về dạng 1D (63 phần tử)
        return norm_coords.flatten().tolist()

    def save_sample(self, hand_landmarks, label, raw_frame):
        """
        Chuẩn hóa và lưu mẫu landmark vào file CSV, đồng thời lưu ảnh gốc (.jpg) vào thư mục tương ứng.
        
        Trả về: Số lượng mẫu hiện tại của cử chỉ này sau khi lưu.
        """
        # 1. Chuẩn hóa landmark
        flat_norm_landmarks = self.normalize_landmarks(hand_landmarks)
        
        # Lấy các mốc thời gian
        now = datetime.now()
        timestamp_csv = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        timestamp_file = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        # 2. Ghi dòng dữ liệu landmark vào CSV
        row_data = flat_norm_landmarks + [label, timestamp_csv, self.session_id]
        with open(self.file_path, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row_data)
            
        # Cập nhật số lượng mẫu trong bộ nhớ
        self.gesture_counts[label] = self.gesture_counts.get(label, 0) + 1
        current_sample_index = self.gesture_counts[label]

        # 3. Tạo thư mục ảnh con cho Gesture này nếu chưa có
        gesture_img_folder = os.path.join(self.images_folder, label)
        if not os.path.exists(gesture_img_folder):
            os.makedirs(gesture_img_folder)
            
        # 4. Ghi ảnh gốc (.jpg) xuống thư mục con
        img_name = f"{label}_{timestamp_file}_{self.session_id}_{current_sample_index}.jpg"
        img_path = os.path.join(gesture_img_folder, img_name)
        try:
            cv2.imwrite(img_path, raw_frame)
        except Exception as e:
            print(f"Error saving raw frame image: {e}")
        
        return current_sample_index
