class GestureManager:
    """
    Quản lý danh sách cử chỉ drone và xoay vòng lựa chọn cử chỉ.
    """
    def __init__(self, target_samples=500):
        # Danh sách các cử chỉ theo yêu cầu điều khiển drone
        self.gestures = [
            'Takeoff',
            'Land',
            'Forward',
            'Backward',
            'Left',
            'Right',
            'Up',
            'Down',
            'Hover'
        ]
        self.current_index = 0
        self.target_samples = target_samples

    def get_current_gesture(self):
        """Trả về tên cử chỉ hiện tại đang được chọn."""
        return self.gestures[self.current_index]

    def next_gesture(self):
        """Chuyển sang cử chỉ tiếp theo trong danh sách (xoay vòng)."""
        self.current_index = (self.current_index + 1) % len(self.gestures)
        return self.get_current_gesture()

    def get_gestures_list(self):
        """Trả về danh sách tất cả các cử chỉ."""
        return self.gestures

    def get_target_samples(self):
        """Trả về số lượng mẫu mục tiêu của mỗi cử chỉ."""
        return self.target_samples
