import cv2

class ROIManager:
    """
    Quản lý Vùng quan tâm (Region of Interest - ROI) ở chính giữa khung hình.
    """
    def __init__(self, frame_width, frame_height, size_ratio=0.45):
        # ROI sẽ là hình vuông ở chính giữa khung hình, kích thước khoảng 45% của chiều nhỏ hơn
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Tính kích thước ROI (đảm bảo là hình vuông cho MediaPipe hoạt động tốt nhất)
        self.roi_size = int(min(frame_width, frame_height) * size_ratio)
        
        # ROI nằm lệch sang bên phải của camera (cách biên phải 50 pixel) giúp người thuận tay phải đưa tay vào thuận tiện hơn
        self.x_start = frame_width - self.roi_size - 50
        self.y_start = (frame_height - self.roi_size) // 2
        self.x_end = self.x_start + self.roi_size
        self.y_end = self.y_start + self.roi_size

    def get_coords(self):
        """Trả về tọa độ (x_start, y_start, x_end, y_end) của ROI."""
        return self.x_start, self.y_start, self.x_end, self.y_end

    def crop_roi(self, frame):
        """Cắt vùng ROI từ frame gốc."""
        return frame[self.y_start:self.y_end, self.x_start:self.x_end]

    def draw_roi(self, frame, is_hand_in_roi=True, has_hand=True):
        """
        Vẽ khung ROI lên frame.
        Màu sắc:
        - Xanh lá nếu có tay và tay nằm hoàn toàn trong ROI.
        - Đỏ nếu có tay nhưng tay thò ra ngoài ROI.
        - Vàng nếu không có tay (chờ đợi người dùng đưa tay vào).
        """
        if not has_hand:
            color = (0, 255, 255) # Màu vàng (BGR) - Cảnh báo/Chờ đợi
            status_text = "Waiting for Hand"
        elif is_hand_in_roi:
            color = (0, 255, 0) # Màu xanh lá - Đạt
            status_text = "ROI OK"
        else:
            color = (0, 0, 255) # Màu đỏ - Không đạt
            status_text = "Move Hand into ROI"

        # Vẽ khung hình chữ nhật nét đứt hoặc nét dày
        cv2.rectangle(frame, (self.x_start, self.y_start), (self.x_end, self.y_end), color, 2)
        
        # Vẽ nhãn ROI ở góc trên bên trái khung ROI
        cv2.putText(frame, f"ROI: {status_text}", (self.x_start, self.y_start - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    def contains_landmarks(self, landmarks_relative, margin=0.01):
        """
        Kiểm tra xem tất cả các landmark (ở dạng tọa độ tương đối [0, 1] của ROI)
        có nằm hoàn toàn trong vùng ROI hay không.
        
        landmarks_relative: Danh sách 21 landmark với thuộc tính x, y, z tương đối so với ROI.
        margin: Khoảng đệm an toàn từ biên để tránh tay chạm sát mép.
        """
        if not landmarks_relative:
            return False
            
        for lm in landmarks_relative:
            # MediaPipe trả về tọa độ tương đối từ 0.0 đến 1.0 trong ảnh đầu vào
            if lm.x < margin or lm.x > (1.0 - margin) or lm.y < margin or lm.y > (1.0 - margin):
                return False
        return True

    def convert_to_global(self, x_rel, y_rel):
        """Chuyển đổi tọa độ tương đối từ ROI sang tọa độ tuyệt đối trên frame gốc."""
        abs_x = int(self.x_start + x_rel * self.roi_size)
        abs_y = int(self.y_start + y_rel * self.roi_size)
        return abs_x, abs_y
