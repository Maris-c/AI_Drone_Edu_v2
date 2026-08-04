import cv2
import numpy as np

class Preprocessor:
    """
    Tiền xử lý hình ảnh vùng ROI trước khi đưa vào MediaPipe Hands.
    """
    def __init__(self, target_size=(256, 256)):
        self.target_size = target_size
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def calculate_brightness(self, bgr_frame):
        """
        Tính toán độ sáng trung bình của ảnh (sử dụng kênh V của HSV).
        """
        hsv = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        return np.mean(v_channel)

    def preprocess(self, roi_frame):
        """
        Tiền xử lý vùng ROI:
        Frame -> Crop ROI -> Resize -> Convert RGB -> Median Blur nhẹ -> CLAHE nếu ảnh tối -> Trả về ảnh RGB tiền xử lý.
        
        Trả về: (preprocessed_rgb, brightness)
        """
        # 1. Tính độ sáng trung bình từ ROI gốc (ảnh BGR)
        brightness = self.calculate_brightness(roi_frame)
        
        # 2. Resize về kích thước cố định để chuẩn hóa đầu vào
        resized = cv2.resize(roi_frame, self.target_size)
        
        # 3. Chuyển sang hệ màu RGB (MediaPipe yêu cầu RGB)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # 4. Áp dụng Median Blur nhẹ để giảm nhiễu hạt
        blurred = cv2.medianBlur(rgb, 3)
        
        # 5. Nếu ảnh tối (độ sáng trung bình < 80), áp dụng CLAHE để tăng cường độ tương phản
        if brightness < 80:
            lab = cv2.cvtColor(blurred, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            cl = self.clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            final_rgb = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
        else:
            final_rgb = blurred
            
        return final_rgb, brightness
