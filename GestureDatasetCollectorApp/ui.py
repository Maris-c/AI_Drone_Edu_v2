import cv2
import numpy as np

class UIManager:
    """
    Quản lý giao diện người dùng hiển thị trên một cửa sổ OpenCV duy nhất.
    Thiết kế bảng điều khiển telemetry chuyên nghiệp, chia màn hình thành 2 phần:
    - Bên trái (75%): Camera Feed, ROI box, Hand Skeleton, và Status Bar nằm ở dưới cùng.
    - Bên phải (25%): Dashboard điều khiển chi tiết (Session Info, Quality Checkmarks, Dataset Balance, Hotkeys).
    """
    def __init__(self, window_name="Gesture Dataset Collector", width=1280, height=720):
        self.window_name = window_name
        self.width = width
        self.height = height
        
        # Phân chia tỷ lệ chiều rộng
        self.cam_width = int(width * 0.75)  # 960px
        self.info_width = width - self.cam_width  # 320px
        
        # Chiều cao của Status Bar ở dưới cùng
        self.status_bar_height = 30
        self.main_height = self.height - self.status_bar_height  # 690px
        
        # Khởi tạo canvas trống màu đen
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Bảng màu sắc (BGR)
        self.COLOR_BG = (22, 22, 22)           # Nền bảng thông tin (Màu đen xám rất sẫm)
        self.COLOR_PANEL_BG = (35, 35, 35)     # Nền các khung chứa
        self.COLOR_TEXT_MAIN = (245, 245, 245)  # Chữ chính (Trắng sữa)
        self.COLOR_TEXT_MUTED = (150, 150, 150) # Chữ phụ (Xám nhạt)
        
        # Màu trạng thái
        self.COLOR_OK = (80, 200, 120)         # Xanh lá (Đạt) - Emerald Green
        self.COLOR_WARN = (50, 215, 255)        # Vàng (Cảnh báo) - Amber/Yellow
        self.COLOR_FAIL = (60, 60, 235)         # Đỏ (Không đạt) - Crimson Red
        self.COLOR_STATUS_BG = (30, 30, 30)     # Nền thanh trạng thái

        # Tạo cửa sổ OpenCV và đặt tên
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)

    def draw_progress_bar(self, img, x, y, w, h, val, max_val, color):
        """Vẽ thanh tiến trình lên ảnh."""
        # Vẽ viền ngoài
        cv2.rectangle(img, (x, y), (x + w, y + h), (60, 60, 60), 1)
        # Tính chiều rộng tiến trình
        progress_w = int(w * (val / max_val)) if max_val > 0 else 0
        progress_w = min(progress_w, w)
        # Vẽ ruột tiến trình
        if progress_w > 0:
            cv2.rectangle(img, (x, y), (x + progress_w, y + h), color, -1)

    def draw_checkmark(self, img, x, y, is_ok):
        """Vẽ dấu check ✔ (màu xanh lá) hoặc ✖ (màu đỏ) bằng đường thẳng OpenCV."""
        if is_ok:
            # Dấu tích ✔
            pt1 = (x, y + 7)
            pt2 = (x + 4, y + 11)
            pt3 = (x + 11, y + 2)
            cv2.line(img, pt1, pt2, self.COLOR_OK, 2, cv2.LINE_AA)
            cv2.line(img, pt2, pt3, self.COLOR_OK, 2, cv2.LINE_AA)
        else:
            # Dấu X ✖
            pt1_1 = (x + 1, y + 2)
            pt1_2 = (x + 9, y + 10)
            pt2_1 = (x + 9, y + 2)
            pt2_2 = (x + 1, y + 10)
            cv2.line(img, pt1_1, pt1_2, self.COLOR_FAIL, 2, cv2.LINE_AA)
            cv2.line(img, pt2_1, pt2_2, self.COLOR_FAIL, 2, cv2.LINE_AA)

    def draw_status_item_with_checkmark(self, img, label, status_text, x, y, is_ok, check_color):
        """Vẽ một dòng thông tin trạng thái kiểm tra kèm checkmark ✔/✖."""
        cv2.putText(img, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, self.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        # Vẽ checkmark lệch sang phải một chút
        self.draw_checkmark(img, x + 125, y - 9, is_ok)
        # Viết text trạng thái phía sau checkmark
        cv2.putText(img, status_text, (x + 145, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, check_color, 1, cv2.LINE_AA)

    def draw_ui(self, 
                frame_cam, 
                quality_results, 
                current_gesture, 
                collected_count, 
                target_samples, 
                total_samples,
                fps, 
                rejected_counts, 
                state="IDLE",          # IDLE, COUNTDOWN, COLLECTING
                countdown_val=0, 
                collect_progress=0,     # Mẫu đã thu trong đợt hiện tại
                total_collect_run=0,    # Tổng số mẫu cần thu trong đợt (ví dụ 30-50)
                feedback_text=None,
                feedback_color=None,
                session_id="sess_xxxx",
                dataset_path="dataset",
                camera_id=0,
                elapsed_time_str="00:00:00",
                gesture_counts=None,      # Dict số lượng mẫu của tất cả cử chỉ
                gestures_list=None,       # Danh sách tất cả các cử chỉ
                auto_collect_stats=None,  # Dict chứa: current_frame, saved_frames, rejected_frames
                auto_next_enabled=True,
                next_capture_ratio=0.0):
        
        # 1. Reset canvas
        self.canvas.fill(0)
        
        # 2. Resize camera frame cho vừa vùng 75% bên trái (960x690)
        resized_cam = cv2.resize(frame_cam, (self.cam_width, self.main_height))
        self.canvas[0:self.main_height, 0:self.cam_width] = resized_cam
        
        # 3. Vẽ phân vùng bảng thông tin bên phải (320x690)
        info_panel = self.canvas[0:self.main_height, self.cam_width:self.width]
        info_panel[:] = self.COLOR_BG
        
        # Vẽ đường phân chia giữa Camera và Bảng thông tin
        cv2.line(self.canvas, (self.cam_width, 0), (self.cam_width, self.main_height), (50, 50, 50), 1)

        x_offset = 20
        y_offset = 25

        # --- TIÊU ĐỀ ---
        cv2.putText(info_panel, "GESTURE DATA COLLECTOR", (x_offset, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLOR_TEXT_MAIN, 2, cv2.LINE_AA)
        
        # --- PHÂN VÙNG 1: SESSION INFO ---
        y_offset += 15
        cv2.line(info_panel, (x_offset, y_offset), (self.info_width - x_offset, y_offset), (55, 55, 55), 1)
        
        y_offset += 18
        # Rút gọn đường dẫn hiển thị nếu quá dài
        display_path = dataset_path
        if len(display_path) > 28:
            display_path = "..." + display_path[-25:]
            
        cv2.putText(info_panel, f"Session ID: {session_id}", (x_offset, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        y_offset += 15
        cv2.putText(info_panel, f"Save Dir: {display_path}", (x_offset, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        y_offset += 15
        cv2.putText(info_panel, f"Active Camera ID: {camera_id}", (x_offset, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        y_offset += 15
        cv2.putText(info_panel, f"Session Duration: {elapsed_time_str}", (x_offset, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)

        # --- PHÂN VÙNG 2: CURRENT GESTURE ---
        y_offset += 25
        cv2.rectangle(info_panel, (x_offset, y_offset), (self.info_width - x_offset, y_offset + 58), self.COLOR_PANEL_BG, -1)
        cv2.putText(info_panel, "CURRENT GESTURE", (x_offset + 10, y_offset + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        cv2.putText(info_panel, current_gesture.upper(), (x_offset + 10, y_offset + 36), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLOR_WARN, 2, cv2.LINE_AA)
        
        # Trạng thái Auto-Next bên góc
        auto_next_str = "Auto-Next: ON" if auto_next_enabled else "Auto-Next: OFF"
        cv2.putText(info_panel, auto_next_str, (self.info_width - x_offset - 90, y_offset + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.COLOR_OK if auto_next_enabled else self.COLOR_TEXT_MUTED, 1, cv2.LINE_AA)
        
        # Mẫu hiện tại của cử chỉ
        cv2.putText(info_panel, f"{collected_count} / {target_samples}", (self.info_width - x_offset - 80, y_offset + 36), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)

        # --- PHÂN VÙNG 3: QUALITY CHECKS (Vẽ Checkmark ✔/✖) ---
        y_offset += 78
        cv2.putText(info_panel, "QUALITY CHECKS", (x_offset, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)
        cv2.line(info_panel, (x_offset, y_offset + 6), (self.info_width - x_offset, y_offset + 6), (55, 55, 55), 1)

        y_offset += 22
        checks = quality_results.get("checks", {})
        
        # 1. Brightness
        b_msg = quality_results.get("brightness_status", "Waiting")
        b_color = self.COLOR_OK if checks.get("brightness", False) else self.COLOR_FAIL
        self.draw_status_item_with_checkmark(info_panel, "Brightness", b_msg, x_offset, y_offset, checks.get("brightness", False), b_color)

        # 2. Blur
        y_offset += 20
        bl_msg = quality_results.get("blur_status", "Waiting")
        bl_color = self.COLOR_OK if checks.get("blur", False) else self.COLOR_FAIL
        self.draw_status_item_with_checkmark(info_panel, "Blur (Laplacian)", bl_msg, x_offset, y_offset, checks.get("blur", False), bl_color)

        # 3. Hand count
        y_offset += 20
        h_msg = quality_results.get("hand_status", "Waiting")
        h_color = self.COLOR_OK if checks.get("hand_count", False) else self.COLOR_FAIL
        self.draw_status_item_with_checkmark(info_panel, "Hand Status", h_msg, x_offset, y_offset, checks.get("hand_count", False), h_color)

        # 4. Tracking
        y_offset += 20
        t_msg = quality_results.get("tracking_status", "Waiting")
        t_color = self.COLOR_OK if checks.get("tracking", False) else self.COLOR_FAIL
        self.draw_status_item_with_checkmark(info_panel, "Tracking Status", t_msg, x_offset, y_offset, checks.get("tracking", False), t_color)

        # 5. ROI Boundary
        y_offset += 20
        r_msg = quality_results.get("roi_status", "Waiting")
        r_color = self.COLOR_OK if checks.get("roi", False) else self.COLOR_FAIL
        self.draw_status_item_with_checkmark(info_panel, "ROI Boundaries", r_msg, x_offset, y_offset, checks.get("roi", False), r_color)

        # 6. Distance
        y_offset += 20
        d_msg = quality_results.get("distance_status", "Waiting")
        d_val = quality_results.get("hand_distance", 0.0)
        d_color = self.COLOR_OK if checks.get("distance", False) else self.COLOR_FAIL
        d_str = f"OK ({int(d_val)}px)" if checks.get("distance", False) else f"{d_msg} ({int(d_val)}px)"
        self.draw_status_item_with_checkmark(info_panel, "Distance (Scale)", d_str, x_offset, y_offset, checks.get("distance", False), d_color)

        # 7. Rotation
        y_offset += 20
        rot_msg = quality_results.get("rotation_status", "Waiting")
        rot_val = quality_results.get("hand_angle", 0.0)
        rot_color = self.COLOR_OK if checks.get("rotation", False) else self.COLOR_FAIL
        rot_str = f"OK ({int(rot_val)} deg)" if checks.get("rotation", False) else f"{rot_msg} ({int(rot_val)} deg)"
        self.draw_status_item_with_checkmark(info_panel, "Hand Rotation", rot_str, x_offset, y_offset, checks.get("rotation", False), rot_color)

        # 8. Stability
        y_offset += 20
        stab_msg = quality_results.get("stability_status", "Waiting")
        stab_val = quality_results.get("hand_displacement", 0.0)
        stab_color = self.COLOR_OK if checks.get("stability", False) else self.COLOR_FAIL
        stab_str = f"OK ({stab_val:.1f}px)" if checks.get("stability", False) else f"{stab_msg} ({stab_val:.1f}px)"
        self.draw_status_item_with_checkmark(info_panel, "Hand Stability", stab_str, x_offset, y_offset, checks.get("stability", False), stab_color)

        # --- PHÂN VÙNG 4: DATASET BALANCE (Vẽ lưới 2 cột) ---
        y_offset += 32
        cv2.putText(info_panel, "DATASET BALANCE", (x_offset, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)
        cv2.line(info_panel, (x_offset, y_offset + 6), (self.info_width - x_offset, y_offset + 6), (55, 55, 55), 1)

        y_offset += 18
        if gesture_counts is None:
            gesture_counts = {}
        if gestures_list is None:
            gestures_list = []

        # Vẽ 10 cử chỉ thành 2 cột để tiết kiệm không gian
        for idx, g_name in enumerate(gestures_list):
            col = idx % 2
            row = idx // 2
            
            gx = x_offset + col * 145
            gy = y_offset + row * 24
            
            g_count = gesture_counts.get(g_name, 0)
            
            # Tô màu vàng nếu là cử chỉ đang được chọn
            text_color = self.COLOR_WARN if g_name == current_gesture else self.COLOR_TEXT_MAIN
            
            # Nhãn cử chỉ và số mẫu
            cv2.putText(info_panel, f"{g_name[:8]}: {g_count}", (gx, gy), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, text_color, 1, cv2.LINE_AA)
            
            # Vẽ thanh tiến trình mini ngay dưới nhãn
            self.draw_progress_bar(info_panel, gx, gy + 4, 125, 4, g_count, target_samples, 
                                   self.COLOR_OK if g_count >= target_samples else self.COLOR_WARN)

        # --- PHÂN VÙNG 5: KEYBOARD HOTKEYS ---
        y_offset = self.main_height - 118
        cv2.rectangle(info_panel, (x_offset, y_offset), (self.info_width - x_offset, self.main_height - 12), (40, 40, 40), -1)
        cv2.putText(info_panel, "KEYBOARD HOTKEYS", (x_offset + 10, y_offset + 18), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_WARN, 1, cv2.LINE_AA)
        
        cv2.putText(info_panel, "[SPACE] Manual Capture (1 sample)", (x_offset + 10, y_offset + 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)
        cv2.putText(info_panel, "[S]     Toggle Auto Collect (On/Off)", (x_offset + 10, y_offset + 52), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)
        cv2.putText(info_panel, "[N]     Cycle Next Gesture", (x_offset + 10, y_offset + 69), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)
        cv2.putText(info_panel, "[ESC]   Save and Exit Program", (x_offset + 10, y_offset + 86), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)

        # --- DRAW STATS OVERLAYS ON CAMERA AREA ---
        if state == "COUNTDOWN":
            overlay = self.canvas.copy()
            cv2.rectangle(overlay, (0, 0), (self.cam_width, self.main_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.4, self.canvas, 0.6, 0, self.canvas)
            
            text = str(countdown_val)
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 4.0
            thick = 10
            (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thick)
            tx = (self.cam_width - text_w) // 2
            ty = (self.main_height + text_h) // 2
            cv2.putText(self.canvas, text, (tx, ty), font, scale, self.COLOR_WARN, thick, cv2.LINE_AA)
            cv2.putText(self.canvas, "Get Ready!", (tx - 80, ty + 80), font, 1.0, self.COLOR_TEXT_MAIN, 2, cv2.LINE_AA)
            
        elif state == "COLLECTING":
            # Panel thống kê đợt thu thập tự động nâng cấp
            panel_w = 420
            panel_h = 110
            px = 20
            py = 20
            cv2.rectangle(self.canvas, (px, py), (px + panel_w, py + panel_h), (20, 20, 20), -1)
            cv2.rectangle(self.canvas, (px, py), (px + panel_w, py + panel_h), self.COLOR_OK, 1)
            
            # Đọc thống kê
            if auto_collect_stats is None:
                auto_collect_stats = {"current_frame": 0, "saved_frames": 0, "rejected_frames": 0}
                
            cur_f = auto_collect_stats.get("current_frame", 0)
            saved_f = auto_collect_stats.get("saved_frames", 0)
            rej_f = auto_collect_stats.get("rejected_frames", 0)
            
            cv2.putText(self.canvas, f"AUTO COLLECTING: {current_gesture.upper()}", 
                        (px + 15, py + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_OK, 2, cv2.LINE_AA)
            
            cv2.putText(self.canvas, f"Processed: {cur_f}", 
                        (px + 15, py + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)
            cv2.putText(self.canvas, f"Saved: {saved_f}", 
                        (px + 15, py + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_OK, 1, cv2.LINE_AA)
            cv2.putText(self.canvas, f"Rejected: {rej_f}", 
                        (px + 15, py + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_FAIL, 1, cv2.LINE_AA)
            
            # Đếm ngược 0.5s chụp tiếp theo:
            next_pct = next_capture_ratio * 100
            cv2.putText(self.canvas, f"Next Photo: {next_pct:.0f}%", 
                        (px + 230, py + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_WARN, 1, cv2.LINE_AA)
            self.draw_progress_bar(self.canvas, px + 230, py + 58, 170, 6, int(next_pct), 100, self.COLOR_WARN)
            
            # Tín hiệu cảnh báo nhấp nháy chuẩn bị chụp
            if next_pct >= 70:
                cv2.putText(self.canvas, "READY TO SNAP!", (px + 230, py + 85), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_WARN, 1, cv2.LINE_AA)

        # --- DRAW GUIDE DIALOG ON CAMERA AREA IF NOT VALID ---
        if state == "IDLE":
            overall_valid = quality_results.get("overall_valid", False)
            reject_reason = quality_results.get("reject_reason", None)
            
            if not overall_valid:
                text_guide = ""
                guide_color = self.COLOR_WARN
                
                if reject_reason == "No Hand":
                    text_guide = "Place your hand inside the ROI box"
                elif reject_reason == "Outside ROI":
                    text_guide = "Move hand entirely into the ROI box"
                    guide_color = self.COLOR_FAIL
                elif reject_reason == "Only One Hand":
                    text_guide = "Ensure only one hand is visible"
                    guide_color = self.COLOR_FAIL
                elif reject_reason == "Move Closer":
                    text_guide = "Move your hand CLOSER to camera"
                    guide_color = self.COLOR_WARN
                elif reject_reason == "Move Back":
                    text_guide = "Move your hand FURTHER from camera"
                    guide_color = self.COLOR_WARN
                elif reject_reason == "Blur":
                    text_guide = "Hold hand steady - Image is Blurry"
                    guide_color = self.COLOR_FAIL
                elif reject_reason in ["Too Dark", "Too Bright"]:
                    text_guide = f"Adjust light - Environment is {reject_reason}"
                    guide_color = self.COLOR_FAIL
                elif reject_reason == "Rotate Hand":
                    text_guide = "Keep your hand straight - Do not rotate too much"
                    guide_color = self.COLOR_FAIL
                elif reject_reason == "Unstable Hand":
                    text_guide = "Hold your hand steady - Shaking detected"
                    guide_color = self.COLOR_FAIL
                elif reject_reason == "Tracking Lost":
                    text_guide = "MediaPipe Tracking Lost - Re-position hand"
                    guide_color = self.COLOR_FAIL
                
                if text_guide:
                    box_w = 640
                    box_h = 45
                    bx = (self.cam_width - box_w) // 2
                    by = self.main_height - 75
                    cv2.rectangle(self.canvas, (bx, by), (bx + box_w, by + box_h), (25, 25, 25), -1)
                    cv2.rectangle(self.canvas, (bx, by), (bx + box_w, by + box_h), guide_color, 1)
                    
                    (tw, th), _ = cv2.getTextSize(text_guide, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
                    cv2.putText(self.canvas, text_guide, (bx + (box_w - tw) // 2, by + (box_h + th) // 2), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, guide_color, 1, cv2.LINE_AA)

        # 6. Vẽ thông báo phản hồi (Feedback Message) nếu có
        if feedback_text:
            color = feedback_color if feedback_color is not None else self.COLOR_OK
            box_w = 400
            box_h = 45
            bx = (self.cam_width - box_w) // 2
            by = 135
            cv2.rectangle(self.canvas, (bx, by), (bx + box_w, by + box_h), (25, 25, 25), -1)
            cv2.rectangle(self.canvas, (bx, by), (bx + box_w, by + box_h), color, 1)
            
            (tw, th), _ = cv2.getTextSize(feedback_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            cv2.putText(self.canvas, feedback_text, (bx + (box_w - tw) // 2, by + (box_h + th) // 2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)

        # --- 7. VẼ SYSTEM STATUS BAR Ở DƯỚI CÙNG ---
        status_bar = self.canvas[self.main_height:self.height, 0:self.width]
        status_bar[:] = self.COLOR_STATUS_BG
        # Vẽ đường kẻ ngăn cách status bar
        cv2.line(self.canvas, (0, self.main_height), (self.width, self.main_height), (50, 50, 50), 1)
        
        # Định nghĩa dòng thông báo trạng thái
        sys_status_str = f"System Status: {state} | Camera: ID 0 ({fps:.1f} FPS) | Session ID: {session_id} | Save Path: {dataset_path}"
        cv2.putText(status_bar, sys_status_str, (15, 18), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_TEXT_MAIN, 1, cv2.LINE_AA)

        # 8. Render ra cửa sổ
        cv2.imshow(self.window_name, self.canvas)

    def close(self):
        """Đóng tất cả các cửa sổ OpenCV."""
        cv2.destroyAllWindows()
