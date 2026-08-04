import cv2
import os
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class MediaPipeDetector:
    """
    Wrapper cho MediaPipe Hands sử dụng Tasks API mới (tương thích Python 3.13+).
    Tự động tải model file nếu chưa tồn tại và thực hiện phát hiện landmarks.
    """
    def __init__(self, max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(script_dir, "hand_landmarker.task")
        self._ensure_model_exists()
        
        # Cấu hình Hand Landmarker Options
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        
        # Định nghĩa các kết nối của bàn tay (connections)
        self.connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),      # Ngón cái
            (0, 5), (5, 6), (6, 7), (7, 8),      # Ngón trỏ
            (5, 9), (9, 10), (10, 11), (11, 12),  # Ngón giữa
            (9, 13), (13, 14), (14, 15), (15, 16),# Ngón áp út
            (13, 17), (17, 18), (18, 19), (19, 20),# Ngón út
            (0, 17),                             # Cổ tay nối ngón út
            (5, 9), (9, 13), (13, 17)            # Nối ngang gốc các ngón tay
        ]

    def _ensure_model_exists(self):
        """Tự động tải file model hand_landmarker.task từ Google CDN nếu chưa có."""
        if not os.path.exists(self.model_path):
            print("Downloading hand_landmarker.task model (approx. 5.6 MB)...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            try:
                urllib.request.urlretrieve(url, self.model_path)
                print("Model downloaded successfully.")
            except Exception as e:
                print(f"Error downloading model: {e}")
                raise e

    def detect(self, rgb_image):
        """
        Phát hiện bàn tay trên ảnh RGB (ROI đã tiền xử lý).
        Trả về đối tượng kết quả HandLandmarkerResult.
        """
        # Chuyển đổi numpy array sang MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
        # Thực hiện phát hiện
        results = self.detector.detect(mp_image)
        return results

    def draw_landmarks_global(self, frame, hand_landmarks, roi_manager, is_valid=True):
        """
        Vẽ 21 landmarks và các đường nối lên khung hình gốc (frame camera lớn),
        sau khi chuyển đổi tọa độ tương đối của ROI thành tọa độ tuyệt đối trên frame gốc.
        
        Màu sắc:
        - Xanh lá nếu đạt chất lượng (is_valid=True)
        - Đỏ nếu không đạt chất lượng (is_valid=False)
        
        Chú ý: Với Tasks API, hand_landmarks trực tiếp là một list chứa 21 landmark có thuộc tính x, y, z.
        """
        color_line = (0, 255, 0) if is_valid else (0, 0, 255)
        color_point = (255, 255, 255) # Điểm tròn màu trắng
        
        # 1. Chuyển đổi toàn bộ 21 landmark sang tọa độ tuyệt đối trên frame gốc
        landmarks_abs = []
        for lm in hand_landmarks:
            abs_x, abs_y = roi_manager.convert_to_global(lm.x, lm.y)
            landmarks_abs.append((abs_x, abs_y))

        # 2. Vẽ các đường kết nối (connections)
        for connection in self.connections:
            start_idx = connection[0]
            end_idx = connection[1]
            if start_idx < len(landmarks_abs) and end_idx < len(landmarks_abs):
                pt1 = landmarks_abs[start_idx]
                pt2 = landmarks_abs[end_idx]
                cv2.line(frame, pt1, pt2, color_line, 2)

        # 3. Vẽ các điểm landmark
        for idx, pt in enumerate(landmarks_abs):
            # Wrist (landmark 0) và ngón trỏ/giữa vẽ to hơn một chút để đánh dấu
            if idx in [0, 5, 9, 13, 17]:
                cv2.circle(frame, pt, 6, color_line, -1)
                cv2.circle(frame, pt, 3, color_point, -1)
            else:
                cv2.circle(frame, pt, 4, color_line, -1)
                cv2.circle(frame, pt, 2, color_point, -1)

    def close(self):
        """Giải phóng bộ phát hiện MediaPipe."""
        self.detector.close()
