import cv2
import numpy as np

class QualityChecker:
    """
    Kiểm tra chất lượng dữ liệu đầu vào và các tiêu chí chuẩn hóa trước khi lưu landmark.
    Đã được mở rộng để hỗ trợ kiểm tra góc xoay bàn tay, độ ổn định bàn tay và điểm tin cậy MediaPipe.
    """
    def __init__(self, 
                 min_brightness=50.0, 
                 max_brightness=220.0, 
                 min_blur_var=80.0, 
                 min_distance=40.0, 
                 max_distance=145.0,
                 max_rotation_angle=30.0,
                 max_stability_displacement=3.5,
                 min_tracking_confidence=0.75):
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_blur_var = min_blur_var
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.max_rotation_angle = max_rotation_angle
        self.max_stability_displacement = max_stability_displacement
        self.min_tracking_confidence = min_tracking_confidence

    def check_brightness(self, brightness):
        """Kiểm tra ánh sáng."""
        if brightness < self.min_brightness:
            return False, "Too Dark"
        elif brightness > self.max_brightness:
            return False, "Too Bright"
        return True, "OK"

    def check_blur(self, roi_frame):
        """Kiểm tra độ mờ sử dụng Laplacian Variance."""
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        blur_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_var < self.min_blur_var:
            return False, "Blur"
        return True, "OK"

    def check_hand_count(self, hand_landmarks_list):
        """Kiểm tra số lượng bàn tay trong ROI."""
        if not hand_landmarks_list:
            return False, "No Hand"
        elif len(hand_landmarks_list) > 1:
            return False, "Only One Hand"
        return True, "OK"

    def check_roi_boundaries(self, landmarks_relative, roi_manager):
        """Kiểm tra tất cả 21 landmark có nằm trong biên ROI."""
        if not landmarks_relative:
            return False, "No Hand"
        if roi_manager.contains_landmarks(landmarks_relative):
            return True, "OK"
        return False, "Outside ROI"

    def check_distance(self, landmarks_relative):
        """Kiểm tra khoảng cách tay (Wrist -> Middle MCP)."""
        if not landmarks_relative or len(landmarks_relative) < 10:
            return False, "No Hand", 0.0

        wrist = landmarks_relative[0]
        middle_mcp = landmarks_relative[9]

        # Tính khoảng cách 2D trên hệ tọa độ ảo 256x256 của ROI
        dx = (middle_mcp.x - wrist.x) * 256
        dy = (middle_mcp.y - wrist.y) * 256
        dist = np.sqrt(dx**2 + dy**2)

        if dist < self.min_distance:
            return False, "Move Closer", dist
        elif dist > self.max_distance:
            return False, "Move Back", dist
        return True, "OK", dist

    def check_rotation(self, landmarks_relative, label="Takeoff"):
        """
        Kiểm tra góc xoay bàn tay (Rotate Hand).
        Tính góc của vector từ Wrist (0) đến Middle MCP (9) so với phương thẳng đứng hướng lên (hoặc hướng xuống với Down).
        """
        if not landmarks_relative or len(landmarks_relative) < 10:
            return False, "No Hand", 0.0

        wrist = landmarks_relative[0]
        middle_mcp = landmarks_relative[9]

        # Trục y của ảnh hướng xuống
        dx = middle_mcp.x - wrist.x
        dy = middle_mcp.y - wrist.y

        # Nếu cử chỉ là Down (dislike), vector hướng xuống thẳng đứng có dy dương
        if label == "Down":
            # Tính góc lệch so với phương thẳng đứng hướng xuống (0, 1)
            angle_rad = np.arctan2(dx, dy)
        else:
            # Tính góc lệch so với phương thẳng đứng hướng lên (0, -1)
            angle_rad = np.arctan2(dx, -dy)

        angle_deg = np.degrees(angle_rad) # Góc từ -180 đến 180 độ
        abs_angle = np.abs(angle_deg)
        
        max_angle = 110.0 if label in ["Up", "Down", "Hover"] else self.max_rotation_angle
        
        if abs_angle > max_angle:
            return False, "Rotate Hand", abs_angle
        return True, "OK", abs_angle

    def check_stability(self, landmarks_relative, prev_landmarks):
        """
        Kiểm tra độ ổn định bàn tay (Hold Hand Steady).
        Tính khoảng cách di chuyển trung bình của 21 landmark so với frame trước đó.
        """
        if not landmarks_relative or not prev_landmarks:
            # Nếu không có frame trước, coi như ổn định để tránh chặn ngay từ đầu
            return True, "OK", 0.0

        displacements = []
        for curr_lm, prev_lm in zip(landmarks_relative, prev_landmarks):
            dx = (curr_lm.x - prev_lm.x) * 256
            dy = (curr_lm.y - prev_lm.y) * 256
            displacements.append(np.sqrt(dx**2 + dy**2))

        mean_disp = np.mean(displacements)
        if mean_disp > self.max_stability_displacement:
            return False, "Unstable Hand", mean_disp
        return True, "OK", mean_disp

    def check_tracking_confidence(self, mp_confidence):
        """Kiểm tra điểm tin cậy tracking của MediaPipe."""
        if mp_confidence < self.min_tracking_confidence:
            return False, "Tracking Lost", mp_confidence
        return True, "OK", mp_confidence

    def evaluate_frame(self, roi_frame, brightness, hand_landmarks_list, roi_manager, prev_landmarks=None, mp_confidence=1.0, current_label="Takeoff"):
        """
        Đánh giá toàn diện chất lượng của một frame.
        Trả về kết quả kiểm tra cho từng tiêu chí và trạng thái hợp lệ chung.
        """
        # Lưu các giá trị ban đầu để khôi phục
        original_min_distance = self.min_distance
        original_max_distance = self.max_distance
        
        # Nới lỏng khoảng cách cho các cử chỉ tay khép/like/dislike
        if current_label in ["Up", "Down", "Hover"]:
            self.min_distance = 30.0
            self.max_distance = 160.0
            
        try:
            # Dict lưu trạng thái của từng check đơn lẻ (dùng để vẽ checkmark ✔/✖)
            checks = {
                "brightness": False,
                "blur": False,
                "hand_count": False,
                "distance": False,
                "roi": False,
                "tracking": False,
                "rotation": False,
                "stability": False
            }

            results = {
                "checks": checks,
                "brightness_status": "Waiting",
                "blur_status": "Waiting",
                "hand_status": "Waiting",
                "roi_status": "Waiting",
                "distance_status": "Waiting",
                "tracking_status": "Waiting",
                "rotation_status": "Waiting",
                "stability_status": "Waiting",
                "hand_distance": 0.0,
                "hand_angle": 0.0,
                "hand_displacement": 0.0,
                "mp_confidence": 0.0,
                "overall_valid": False,
                "reject_reason": None
            }

            # 1. Kiểm tra ánh sáng
            br_ok, br_msg = self.check_brightness(brightness)
            checks["brightness"] = br_ok
            results["brightness_status"] = br_msg
            if not br_ok:
                results["reject_reason"] = br_msg
                return results

            # 2. Kiểm tra độ mờ
            blur_ok, blur_msg = self.check_blur(roi_frame)
            checks["blur"] = blur_ok
            results["blur_status"] = blur_msg
            if not blur_ok:
                results["reject_reason"] = "Blur"
                return results

            # 3. Kiểm tra số lượng tay
            hand_ok, hand_msg = self.check_hand_count(hand_landmarks_list)
            checks["hand_count"] = hand_ok
            results["hand_status"] = hand_msg
            if not hand_ok:
                results["reject_reason"] = hand_msg
                results["tracking_status"] = "Lost" if hand_msg == "No Hand" else "OK"
                return results

            # Lấy landmark tương đối
            landmarks_relative = hand_landmarks_list[0]

            # 4. Kiểm tra tracking confidence của MediaPipe
            track_ok, track_msg, conf_val = self.check_tracking_confidence(mp_confidence)
            checks["tracking"] = track_ok
            results["mp_confidence"] = conf_val
            results["tracking_status"] = f"OK ({conf_val:.2f})" if track_ok else track_msg
            if not track_ok:
                results["reject_reason"] = "Tracking Lost"
                return results

            # 5. Kiểm tra ranh giới ROI
            roi_ok, roi_msg = self.check_roi_boundaries(landmarks_relative, roi_manager)
            checks["roi"] = roi_ok
            results["roi_status"] = roi_msg
            if not roi_ok:
                results["reject_reason"] = roi_msg
                return results

            # 6. Kiểm tra khoảng cách
            dist_ok, dist_msg, dist_val = self.check_distance(landmarks_relative)
            checks["distance"] = dist_ok
            results["hand_distance"] = dist_val
            results["distance_status"] = dist_msg
            if not dist_ok:
                results["reject_reason"] = dist_msg
                return results

            # 7. Kiểm tra góc xoay (Rotate Hand)
            rot_ok, rot_msg, rot_val = self.check_rotation(landmarks_relative, label=current_label)
            checks["rotation"] = rot_ok
            results["hand_angle"] = rot_val
            results["rotation_status"] = rot_msg
            if not rot_ok:
                results["reject_reason"] = rot_msg
                return results

            # 8. Kiểm tra độ ổn định bàn tay (Steady Hand)
            stab_ok, stab_msg, stab_val = self.check_stability(landmarks_relative, prev_landmarks)
            checks["stability"] = stab_ok
            results["hand_displacement"] = stab_val
            results["stability_status"] = stab_msg
            if not stab_ok:
                results["reject_reason"] = "Unstable Hand"
                return results

            # Nếu vượt qua tất cả
            results["overall_valid"] = True
            return results
        finally:
            # Luôn khôi phục lại giá trị giới hạn khoảng cách mặc định
            self.min_distance = original_min_distance
            self.max_distance = original_max_distance
