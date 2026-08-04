import os
import pandas as pd
import numpy as np

def run_stratified_split(input_file="dataset/gesture_dataset_clean.csv", output_dir="dataset"):
    print("=" * 60)
    print("       GESTURE DATASET STRATIFIED SPLITTER (70/20/10)")
    print("=" * 60)
    
    if not os.path.exists(input_file):
        print(f"Error: Cleaned dataset '{input_file}' not found.")
        print("Please run the eda_clean.py tool first to produce it.")
        return

    # Đọc dữ liệu
    print(f"\n[1/4] Reading dataset: {input_file} ...")
    df = pd.read_csv(input_file)
    total_samples = len(df)
    print(f"-> Total samples in dataset: {total_samples}")
    
    if 'label' not in df.columns:
        print("Error: 'label' column is missing from dataset. Cannot split.")
        return

    # Khởi tạo các list chứa dataframe tạm thời
    train_dfs = []
    val_dfs = []
    test_dfs = []
    
    # Lưu thống kê phân phối
    stats = {}
    
    print("\n[2/4] Splitting dataset per gesture class (Stratified)...")
    # Nhóm theo cột 'label' để chia đều từng cử chỉ
    grouped = df.groupby('label')
    
    for label, group in grouped:
        # Xáo trộn nhóm một cách ngẫu nhiên với seed cố định để có thể tái sinh kết quả (reproducibility)
        group_shuffled = group.sample(frac=1, random_state=42).reset_index(drop=True)
        n = len(group_shuffled)
        
        # Tính kích thước phân phối cho nhóm này
        n_train = int(round(n * 0.70))
        n_val = int(round(n * 0.20))
        n_test = n - n_train - n_val  # Phần còn lại để tránh hao hụt mẫu
        
        # Cắt nhóm thành các tập Train, Validation, Test
        train_group = group_shuffled.iloc[:n_train]
        val_group = group_shuffled.iloc[n_train:n_train + n_val]
        test_group = group_shuffled.iloc[n_train + n_val:]
        
        train_dfs.append(train_group)
        val_dfs.append(val_group)
        test_dfs.append(test_group)
        
        # Lưu số liệu thống kê
        stats[label] = {
            "total": n,
            "train": len(train_group),
            "val": len(val_group),
            "test": len(test_group)
        }

    # Ghép các nhóm đã chia và xáo trộn lại một lần cuối cho tập dữ liệu tổng thể trộn đều
    df_train = pd.concat(train_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
    df_val = pd.concat(val_dfs).sample(frac=1, random_state=42).reset_index(drop=True)
    df_test = pd.concat(test_dfs).sample(frac=1, random_state=42).reset_index(drop=True)

    print("\n[3/4] Exporting split subsets to CSV files...")
    # Tạo thư mục đầu ra nếu chưa có
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    train_path = os.path.join(output_dir, "train.csv")
    val_path = os.path.join(output_dir, "validation.csv")
    test_path = os.path.join(output_dir, "test.csv")
    
    df_train.to_csv(train_path, index=False)
    df_val.to_csv(val_path, index=False)
    df_test.to_csv(test_path, index=False)
    
    print(f" * Saved Train (70%)      : {train_path} ({len(df_train)} samples)")
    print(f" * Saved Validation (20%) : {val_path} ({len(df_val)} samples)")
    print(f" * Saved Test (10%)       : {test_path} ({len(df_test)} samples)")

    # --- 4. HIỂN THỊ BÁO CÁO THỐNG KÊ PHÂN PHỐI ---
    print("\n[4/4] Stratified Split Distribution Summary:")
    print("-" * 75)
    print(f" {'Gesture Name':<15} | {'Total':<8} | {'Train (70%)':<12} | {'Val (20%)':<10} | {'Test (10%)':<10}")
    print("-" * 75)
    
    for label, count_dict in sorted(stats.items()):
        total = count_dict["total"]
        tr = count_dict["train"]
        vl = count_dict["val"]
        ts = count_dict["test"]
        
        tr_pct = (tr / total) * 100 if total > 0 else 0.0
        vl_pct = (vl / total) * 100 if total > 0 else 0.0
        ts_pct = (ts / total) * 100 if total > 0 else 0.0
        
        tr_str = f"{tr} ({tr_pct:.1f}%)"
        vl_str = f"{vl} ({vl_pct:.1f}%)"
        ts_str = f"{ts} ({ts_pct:.1f}%)"
        
        print(f" {label:<15} | {total:<8} | {tr_str:<12} | {vl_str:<10} | {ts_str:<10}")
        
    print("-" * 75)
    print(f" {'OVERALL TOTAL':<15} | {total_samples:<8} | {len(df_train):<12} | {len(df_val):<10} | {len(df_test):<10}")
    print("-" * 75)
    print("\nSplit completed successfully and class distribution is perfectly matched!")
    print("=" * 60)

if __name__ == "__main__":
    run_stratified_split()
