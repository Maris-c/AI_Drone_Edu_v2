import cv2

class CameraManager:
    """
    Quản lý luồng video từ webcam bằng OpenCV.
    """
    def __init__(self, device_index=0, width=640, height=480):
        self.device_index = device_index
        self.cap = cv2.VideoCapture(self.device_index)
        
        # Thiết lập độ phân giải mong muốn
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Đọc thử một khung hình để lấy độ phân giải thực tế
        success, frame = self.cap.read()
        if success:
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            self.width = width
            self.height = height
            print(f"Warning: Could not test read from camera {device_index}.")

    def is_opened(self):
        return self.cap.isOpened()

    def read_frame(self):
        """
        Đọc một khung hình từ camera.
        Trả về: (success, frame)
        """
        success, frame = self.cap.read()
        if success:
            # Lật frame theo chiều ngang để giống như nhìn vào gương (tiện cho người dùng)
            frame = cv2.flip(frame, 1)
        return success, frame

    def release(self):
        """
        Giải phóng tài nguyên camera.
        """
        if self.cap.isOpened():
            self.cap.release()
            print("Camera released.")
