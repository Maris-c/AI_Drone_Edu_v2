import cv2
import time
import os
from camera import CameraManager
from roi import ROIManager
from preprocessing import Preprocessor
from quality_checker import QualityChecker
from mediapipe_detector import MediaPipeDetector
from dataset_manager import DatasetManager
from gesture_manager import GestureManager
from ui import UIManager

class GestureDatasetCollectorApp:
    """
    Lớp điều khiển chính nâng cấp cho ứng dụng Gesture Dataset Collector.
    Quản lý máy trạng thái, xử lý video thời gian thực, đo lường sự ổn định,
    góc xoay bàn tay và đồng bộ hóa các luồng dữ liệu.
    """
    def __init__(self):
        print("Initializing upgraded modules...")
        # 1. Khởi tạo phần cứng và thuật toán
        self.camera = CameraManager(device_index=0, width=640, height=480)
        self.roi = ROIManager(self.camera.width, self.camera.height, size_ratio=0.45)
        self.preprocessor = Preprocessor(target_size=(256, 256))
        
        # Cấu hình Quality Checker mở rộng với các ngưỡng kiểm soát chặt chẽ
        self.checker = QualityChecker(
            min_brightness=50.0, 
            max_brightness=220.0, 
            min_blur_var=80.0, 
            min_distance=40.0, 
            max_distance=145.0,
            max_rotation_angle=30.0,          # Góc xoay tay cho phép <= 30 độ
            max_stability_displacement=3.5,    # Độ lệch dịch chuyển tay <= 3.5px
            min_tracking_confidence=0.75       # Độ tin cậy MP tracking >= 75%
        )
        
        self.detector = MediaPipeDetector(
            max_num_hands=2, 
            min_detection_confidence=0.7, 
            min_tracking_confidence=0.7
        )
        
        # 2. Khởi tạo quản lý dữ liệu và danh sách cử chỉ
        self.dataset = DatasetManager(folder_path="dataset", file_name="gesture_dataset.csv")
        self.gesture_mgr = GestureManager(target_samples=500)
        
        # 3. Khởi tạo giao diện người dùng
        self.ui = UIManager(window_name="Gesture Dataset Collector", width=1280, height=720)

        # 4. Biến cờ cấu hình hành vi
        self.auto_next_gesture = True  # Tự động nhảy sang cử chỉ tiếp theo khi gom đủ target
        
        # 5. Các biến trạng thái ứng dụng
        self.state = "IDLE"  # IDLE, COUNTDOWN, COLLECTING
        self.countdown_duration = 3.0 # giây
        self.countdown_start_time = 0.0
        self.countdown_val = 3
        
        # Quản lý phiên tự động thu thập mẫu hiện tại
        self.collect_target = 40      # Thu thập 40 mẫu đạt chuẩn mỗi đợt nhấn S
        self.collect_count = 0
        self.auto_collect_stats = {
            "current_frame": 0,
            "saved_frames": 0,
            "rejected_frames": 0
        }
        
        # Bộ nhớ lưu landmark trước đó để đo độ rung lắc (Hold Hand Steady)
        self.prev_landmarks = None
        
        # Tính toán thời gian hoạt động của Session
        self.session_start_time = time.time()
        
        # Thống kê chi tiết số lượng frame bị loại theo 9 nguyên nhân
        self.rejected_counts = {
            "Too Dark": 0,
            "Too Bright": 0,
            "Blur": 0,
            "Outside ROI": 0,
            "Only One Hand": 0,
            "Move Closer": 0,
            "Move Back": 0,
            "Tracking Lost": 0,
            "Rotate Hand": 0,
            "Unstable Hand": 0,
            "No Hand": 0
        }
        
        # Tính toán FPS mượt mà
        self.fps = 0.0
        self.prev_frame_time = time.time()
        
        # Thông báo phản hồi thủ công (Feedback messages)
        self.feedback_text = None
        self.feedback_color = None
        self.feedback_expires = 0.0
        
        # Quản lý thời gian chụp tự động giãn cách 0.5s
        self.last_save_time = 0.0
        self.next_capture_ratio = 0.0

    def run(self):
        """Vòng lặp chính của ứng dụng."""
        print("Starting Gesture Dataset Collector App. Press ESC to exit.")
        if not self.camera.is_opened():
            print("Error: Could not connect to webcam.")
            return

        while True:
            # Kiểm tra xem người dùng có click nút X để đóng cửa sổ OpenCV không
            try:
                if cv2.getWindowProperty(self.ui.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    print("Window closed by user. Exiting...")
                    break
            except Exception:
                print("Window closed by user. Exiting...")
                break

            # 1. Đọc frame camera
            success, frame = self.camera.read_frame()
            if not success:
                print("Error: Cannot read frame from camera.")
                break

            frame_draw = frame.copy()
            
            # 2. Cắt ảnh vùng ROI
            roi_frame = self.roi.crop_roi(frame)
            
            # 3. Tiền xử lý vùng ROI
            preprocessed_rgb, brightness = self.preprocessor.preprocess(roi_frame)
            
            # 4. Chạy MediaPipe Hands
            mp_results = self.detector.detect(preprocessed_rgb)
            hand_landmarks_list = mp_results.hand_landmarks if mp_results.hand_landmarks else []
            
            # Lấy điểm tin cậy classification/tracking bàn tay của MediaPipe
            mp_confidence = 1.0
            if mp_results.handedness and len(mp_results.handedness) > 0:
                # Lấy score của bàn tay đầu tiên được phát hiện
                mp_confidence = mp_results.handedness[0][0].score

            # Lấy cử chỉ hiện tại
            current_gesture = self.gesture_mgr.get_current_gesture()

            # 5. Đánh giá chất lượng frame qua Quality Checker mở rộng
            quality_results = self.checker.evaluate_frame(
                roi_frame=roi_frame, 
                brightness=brightness, 
                hand_landmarks_list=hand_landmarks_list, 
                roi_manager=self.roi,
                prev_landmarks=self.prev_landmarks,
                mp_confidence=mp_confidence,
                current_label=current_gesture
            )

            # 6. Xử lý logic máy trạng thái (State Machine)
            self._handle_state_logic(quality_results, hand_landmarks_list, frame)

            # 7. Cập nhật lưu trữ landmark trước đó để tính Hold Hand Steady
            # Chỉ lưu landmark khi có duy nhất 1 bàn tay trong khung hình
            if quality_results["hand_status"] == "OK":
                self.prev_landmarks = hand_landmarks_list[0]
            else:
                self.prev_landmarks = None

            # 8. Vẽ overlay thông tin bàn tay lên camera frame gốc
            if len(hand_landmarks_list) == 1:
                self.detector.draw_landmarks_global(
                    frame_draw, 
                    hand_landmarks_list[0], 
                    self.roi, 
                    is_valid=quality_results["overall_valid"]
                )
            
            # Vẽ khung ROI
            self.roi.draw_roi(
                frame_draw, 
                is_hand_in_roi=(quality_results["roi_status"] == "OK"), 
                has_hand=(quality_results["hand_status"] != "No Hand")
            )

            # 9. Cập nhật FPS mượt mà
            current_time = time.time()
            elapsed_time = current_time - self.prev_frame_time
            self.prev_frame_time = current_time
            if elapsed_time > 0:
                current_fps = 1.0 / elapsed_time
                self.fps = 0.9 * self.fps + 0.1 * current_fps

            # 10. Tính toán thời gian phiên làm việc (Session Duration)
            session_elapsed = time.time() - self.session_start_time
            hours, rem = divmod(int(session_elapsed), 3600)
            minutes, seconds = divmod(rem, 60)
            elapsed_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            # 11. Cập nhật thông báo phản hồi hết hạn
            if self.feedback_text and time.time() > self.feedback_expires:
                self.feedback_text = None
                self.feedback_color = None

            # Tính toán tỷ lệ chờ chụp tiếp theo
            if self.state == "COLLECTING":
                self.next_capture_ratio = min((time.time() - self.last_save_time) / 0.5, 1.0)
            else:
                self.next_capture_ratio = 0.0

            # Lấy dữ liệu hiển thị và vẽ giao diện
            current_gesture = self.gesture_mgr.get_current_gesture()
            collected_count = self.dataset.get_gesture_counts().get(current_gesture, 0)
            target_samples = self.gesture_mgr.get_target_samples()
            total_samples = self.dataset.get_total_samples()

            self.ui.draw_ui(
                frame_cam=frame_draw,
                quality_results=quality_results,
                current_gesture=current_gesture,
                collected_count=collected_count,
                target_samples=target_samples,
                total_samples=total_samples,
                fps=self.fps,
                rejected_counts=self.rejected_counts,
                state=self.state,
                countdown_val=self.countdown_val,
                collect_progress=self.collect_count,
                total_collect_run=self.collect_target,
                feedback_text=self.feedback_text,
                feedback_color=self.feedback_color,
                session_id=self.dataset.session_id,
                dataset_path=self.dataset.folder_path,
                camera_id=self.camera.device_index,
                elapsed_time_str=elapsed_time_str,
                gesture_counts=self.dataset.get_gesture_counts(),
                gestures_list=self.gesture_mgr.get_gestures_list(),
                auto_collect_stats=self.auto_collect_stats,
                auto_next_enabled=self.auto_next_gesture,
                next_capture_ratio=self.next_capture_ratio
            )

            # 13. Xử lý các sự kiện bàn phím
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # Phím ESC
                print("Exiting program...")
                break
            elif key == 32 and self.state == "IDLE":  # Phím SPACE (chụp thủ công)
                # Chụp thủ công 1 mẫu nếu hợp lệ
                if quality_results["overall_valid"]:
                    self.dataset.save_sample(hand_landmarks_list[0], current_gesture, frame)
                    self.feedback_text = "Manual Sample Saved!"
                    self.feedback_color = self.ui.COLOR_OK
                    self.feedback_expires = time.time() + 1.2
                    print(f"Manual sample saved for gesture: {current_gesture}")
                else:
                    reason = quality_results["reject_reason"]
                    self.feedback_text = f"Save Failed: {reason}"
                    self.feedback_color = self.ui.COLOR_FAIL
                    self.feedback_expires = time.time() + 1.2
                    print(f"Manual sample save failed: {reason}")
            elif (key == ord('s') or key == ord('S')):  # Phím S (Toggle Auto Collect)
                if self.state == "IDLE":
                    # Bắt đầu quy trình đếm ngược tự động thu thập
                    self.state = "COUNTDOWN"
                    self.countdown_start_time = time.time()
                    print("Starting countdown for auto collection...")
                elif self.state in ["COUNTDOWN", "COLLECTING"]:
                    # Tắt chế độ tự động thu thập
                    self.state = "IDLE"
                    self.feedback_text = "Auto Collect Stopped!"
                    self.feedback_color = self.ui.COLOR_WARN
                    self.feedback_expires = time.time() + 1.5
                    print("Auto collection stopped by user.")
            elif (key == ord('n') or key == ord('N')) and self.state == "IDLE":  # Phím N (Next Gesture)
                next_g = self.gesture_mgr.next_gesture()
                print(f"Switched to gesture: {next_g}")

        # 14. Dọn dẹp tài nguyên
        self.camera.release()
        self.detector.close()
        self.ui.close()
        print("Program closed safely.")

    def _handle_state_logic(self, quality_results, hand_landmarks_list, raw_frame):
        """Xử lý chuyển trạng thái và lưu trữ dữ liệu."""
        if self.state == "COUNTDOWN":
            elapsed = time.time() - self.countdown_start_time
            self.countdown_val = int(self.countdown_duration + 1 - elapsed)
            
            if self.countdown_val <= 0:
                self.state = "COLLECTING"
                self.collect_count = 0
                self.last_save_time = time.time()
                self.auto_collect_stats = {
                    "current_frame": 0,
                    "saved_frames": 0,
                    "rejected_frames": 0
                }
                print("Starting auto dataset collection...")
                
        elif self.state == "COLLECTING":
            # Tăng tổng số frame đã xử lý trong đợt thu thập
            self.auto_collect_stats["current_frame"] += 1
            
            # Kiểm tra khoảng thời gian giữa các lần chụp tự động (>= 0.5s)
            if time.time() - self.last_save_time >= 0.5:
                # Chỉ lưu frame đạt toàn bộ Quality Check
                if quality_results["overall_valid"]:
                    current_gesture = self.gesture_mgr.get_current_gesture()
                    
                    # Lưu landmark bàn tay kèm tệp ảnh BGR tương ứng
                    self.dataset.save_sample(hand_landmarks_list[0], current_gesture, raw_frame)
                    
                    self.collect_count += 1
                    self.auto_collect_stats["saved_frames"] = self.collect_count
                    
                    # Cập nhật thời gian lưu mẫu cuối cùng
                    self.last_save_time = time.time()
                    
                    print(f"Auto collected sample: {self.collect_count} for gesture {current_gesture}")
                    
                    # Kiểm tra xem tổng mẫu của cử chỉ hiện tại đã đạt target_samples chưa
                    current_total = self.dataset.get_gesture_counts().get(current_gesture, 0)
                    target_samples = self.gesture_mgr.get_target_samples()
                    
                    if current_total >= target_samples and self.auto_next_gesture:
                        # Tự động nhảy sang Gesture tiếp theo và đưa về IDLE
                        next_g = self.gesture_mgr.next_gesture()
                        self.state = "IDLE"
                        self.feedback_text = f"Target Met! Switched to {next_g}"
                        self.feedback_color = self.ui.COLOR_WARN
                        self.feedback_expires = time.time() + 2.0
                        print(f"Reached target for {current_gesture}. Auto-switched to: {next_g}")
                else:
                    # Tăng số lượng frame bị loại theo đợt tự gom mẫu
                    # (Không reset last_save_time để frame đạt chuẩn kế tiếp được chụp ngay)
                    self.auto_collect_stats["rejected_frames"] += 1
                    
                    # Tăng bộ đếm thống kê 9 loại lỗi chi tiết của hệ thống
                    reason = quality_results["reject_reason"]
                    if reason in self.rejected_counts:
                        self.rejected_counts[reason] += 1
                    elif reason is not None:
                        if "Closer" in reason or "Back" in reason:
                            self.rejected_counts[reason] += 1
                        else:
                            self.rejected_counts[reason] = self.rejected_counts.get(reason, 0) + 1

if __name__ == "__main__":
    app = GestureDatasetCollectorApp()
    app.run()
