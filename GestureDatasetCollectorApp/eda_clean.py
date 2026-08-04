import os
import pandas as pd
import numpy as np

def run_eda_and_cleaning(input_file="dataset/gesture_dataset.csv", output_file="dataset/gesture_dataset_clean.csv"):
    print("=" * 60)
    print("       GESTURE DATASET EXPLORATION & CLEANING TOOL")
    print("=" * 60)
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        print("Please run the Gesture Dataset Collector to gather some samples first.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    if len(lines) == 0:
        print("Dataset file is empty.")
        return
        
    # --- 1. PHÁT HIỆN THIẾU TIÊU ĐỀ (HEADER DETECTION & RECOVERY) ---
    print("\n[1/5] Detecting CSV Header...")
    first_line = lines[0].strip().split(',')
    
    # Kiểm tra xem dòng đầu tiên là header hay dữ liệu số
    is_header_missing = False
    try:
        # Nếu phần tử đầu tiên có thể chuyển đổi thành float (ví dụ 0.0), hoặc là số
        float(first_line[0])
        is_header_missing = True
    except ValueError:
        # Nếu có chữ (như 'x0' hoặc 'label'), thì đó là header hợp lệ
        is_header_missing = False

    # Xác định số lượng cột mong muốn
    if is_header_missing:
        print("-> WARNING: CSV Header is missing (first line contains numeric coordinates)!")
        print("   Automatically generating and recovering standard gesture headers...")
        
        # Đếm số lượng cột của dòng đầu tiên để sinh header phù hợp
        cols_count = len(first_line)
        headers = []
        for i in range(21):
            headers.extend([f"x{i}", f"y{i}", f"z{i}"])
        headers.extend(["label", "timestamp"])
        if cols_count >= 66:
            headers.append("session_id")
        # Thêm các cột bổ sung nếu phát sinh cột dư
        if len(headers) < cols_count:
            for j in range(len(headers), cols_count):
                headers.append(f"extra_col_{j}")
        elif len(headers) > cols_count:
            # Thu nhỏ nếu file cũ thiếu cột
            headers = headers[:cols_count]
            
        expected_cols = len(headers)
        print(f"-> Generated standard headers with {expected_cols} columns.")
        
        # Tất cả các dòng đều là dữ liệu
        data_lines = lines
    else:
        headers = first_line
        expected_cols = len(headers)
        print(f"-> OK: Header found. Columns count: {expected_cols}")
        # Dữ liệu bắt đầu từ dòng 2
        data_lines = lines[1:]

    # --- 2. KIỂM TRA DÒNG LỖI CẤU TRÚC (STRUCTURAL ERRORS) ---
    print("\n[2/5] Checking Structural Line Errors...")
    valid_data_lines = []
    structural_error_rows = []
    
    # Tính số thứ tự dòng tương đối trong file gốc
    start_line_idx = 1 if is_header_missing else 2
    
    for idx, line in enumerate(data_lines, start=start_line_idx):
        cols = line.strip().split(',')
        if len(cols) != expected_cols:
            structural_error_rows.append((idx, len(cols), line.strip()))
        else:
            valid_data_lines.append(line)
            
    num_structural_errors = len(structural_error_rows)
    if num_structural_errors > 0:
        print(f"-> FOUND {num_structural_errors} row(s) with structural column mismatch errors!")
        for row_idx, col_count, content in structural_error_rows[:5]:
            print(f"   * Row {row_idx}: Got {col_count} columns (Expected {expected_cols}). Content: {content[:80]}...")
        if num_structural_errors > 5:
            print(f"   * ... and {num_structural_errors - 5} more structural errors.")
    else:
        print("-> OK: No structural line errors detected.")

    # --- CHUYỂN DỮ LIỆU CẤU TRÚC HỢP LỆ VÀO PANDAS ---
    from io import StringIO
    if is_header_missing:
        # Không có header trong valid_data_lines, gán trực tiếp names=headers
        csv_buffer = StringIO("".join(valid_data_lines))
        df = pd.read_csv(csv_buffer, header=None, names=headers)
    else:
        # Có header, nạp dòng header lên đầu buffer
        csv_buffer = StringIO(lines[0] + "".join(valid_data_lines))
        df = pd.read_csv(csv_buffer)
        
    total_valid_rows = len(df)
    
    # --- 3. KIỂM TRA GIÁ TRỊ TRỐNG/NaN (NaN VALUES) ---
    print("\n[3/5] Checking Missing/NaN Values...")
    nan_counts = df.isnull().sum()
    total_nans = nan_counts.sum()
    
    if total_nans > 0:
        print(f"-> FOUND {total_nans} missing (NaN/Null) cells in the dataset.")
        cols_with_nan = nan_counts[nan_counts > 0]
        for col, count in cols_with_nan.items():
            print(f"   * Column '{col}': {count} missing values")
    else:
        print("-> OK: No missing (NaN) values detected.")

    # --- 4. KIỂM TRA LANDMARK BẤT THƯỜNG (LANDMARK ANOMALIES) ---
    print("\n[4/5] Checking for Landmark Anomalies (Outliers)...")
    
    # Xác định các cột chứa landmark
    landmark_cols = [col for col in df.columns if (col.startswith('x') or col.startswith('y') or col.startswith('z')) and col[1:].isdigit()]
    
    anomalous_rows = []
    
    if len(landmark_cols) > 0:
        # Lọc các giá trị có trị tuyệt đối > 5.0 (outliers vật lý)
        outlier_mask = df[landmark_cols].abs() > 5.0
        outlier_rows = df[outlier_mask.any(axis=1)]
        
        # Kiểm tra xem có hàng nào mà tất cả các landmark (ngoại trừ x0, y0, z0) đều bằng 0.0
        non_wrist_cols = [c for c in landmark_cols if c not in ['x0', 'y0', 'z0']]
        all_zero_mask = (df[non_wrist_cols] == 0.0).all(axis=1)
        all_zero_rows = df[all_zero_mask]
        
        # Hợp nhất các dòng bất thường
        anomalous_indices = set(outlier_rows.index).union(set(all_zero_rows.index))
        anomalous_rows = list(anomalous_indices)
        
        num_anomalies = len(anomalous_rows)
        if num_anomalies > 0:
            print(f"-> FOUND {num_anomalies} row(s) with anomalous landmarks (outliers > 5.0 or empty zero-coordinates).")
            for idx in anomalous_rows[:5]:
                row_label = df.loc[idx, 'label'] if 'label' in df.columns else 'Unknown'
                max_val = df.loc[idx, landmark_cols].abs().max()
                is_zero = idx in all_zero_rows.index
                type_msg = "Zero landmarks" if is_zero else f"Outlier (Max absolute value = {max_val:.2f})"
                print(f"   * Row Index {idx} (Gesture: '{row_label}'): {type_msg}")
            if num_anomalies > 5:
                print(f"   * ... and {num_anomalies - 5} more anomalies.")
        else:
            print("-> OK: No anomalous landmarks detected.")
    else:
        print("-> Warning: No coordinate columns found in the dataset.")

    # --- 5. PHÂN TÍCH THỐNG KÊ GESTURE & ĐỘ LỆCH DỮ LIỆU (EDA) ---
    print("\n[5/5] Analyzing Gesture Distribution & Balance...")
    
    if 'label' in df.columns:
        gesture_counts = df['label'].value_counts()
        num_gestures = len(gesture_counts)
        print(f"-> Total distinct gestures found: {num_gestures}")
        print("\nGesture sample distribution:")
        print("-" * 35)
        print(f" {'Gesture Name':<15} | {'Sample Count':<12}")
        print("-" * 35)
        for gesture, count in gesture_counts.items():
            print(f" {gesture:<15} | {count:<12}")
        print("-" * 35)
        
        # Đánh giá độ lệch dữ liệu
        min_samples = gesture_counts.min()
        max_samples = gesture_counts.max()
        if min_samples > 0:
            imbalance_ratio = max_samples / min_samples
            print(f"-> Imbalance ratio (Max/Min): {imbalance_ratio:.2f}")
            
            if imbalance_ratio > 1.5:
                print("   * WARNING: Data is imbalanced (ratio > 1.5)!")
                print("     Consider collecting more samples for the minority gestures to improve training accuracy.")
            else:
                print("   * OK: Dataset is well-balanced (ratio <= 1.5).")
        else:
            print("-> Error: One or more gestures have 0 samples.")
    else:
        print("-> Error: 'label' column not found in dataset. Cannot perform gesture analysis.")

    # --- 6. LÀM SẠCH VÀ GHI DỮ LIỆU SẠCH (DATA CLEANING) ---
    print("\n[6/6] Sanitizing and exporting dataset...")
    
    # Bỏ các dòng NaN
    df_clean = df.dropna()
    
    # Bỏ các dòng có landmark bất thường
    if len(anomalous_rows) > 0:
        df_clean = df_clean.drop(index=anomalous_rows, errors='ignore')
        
    original_raw_rows = len(lines) if is_header_missing else (len(lines) - 1)
    total_removed = original_raw_rows - len(df_clean)
    retention_rate = (len(df_clean) / original_raw_rows) * 100
    
    # Tạo thư mục đầu ra nếu chưa có
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df_clean.to_csv(output_file, index=False)
    
    print("\nCleaning Summary:")
    print("-" * 50)
    print(f" * Original Raw Rows   : {original_raw_rows}")
    print(f" * Structural Errors   : {num_structural_errors} row(s) removed")
    print(f" * NaN/Null Rows       : {total_valid_rows - len(df.dropna())} row(s) removed")
    print(f" * Outlier/Anomaly Rows: {len(anomalous_rows)} row(s) removed")
    print(f" * Cleaned Rows Kept   : {len(df_clean)}")
    print(f" * Data Kept Ratio     : {retention_rate:.2f}%")
    print(f" * Saved clean file to : {output_file}")
    print("-" * 50)
    print("\nDone! Dataset is ready for Machine Learning training.")
    print("=" * 60)

if __name__ == "__main__":
    run_eda_and_cleaning()
