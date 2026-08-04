import pandas as pd
import numpy as np

class DatasetLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.features = None
        self.labels = None
        self.stats = {}

    def load_and_analyze(self):
        """
        Loads the CSV dataset and analyzes its characteristics.
        Returns a tuple: (success, message, stats_dict)
        """
        try:
            # Load CSV (no header, as MediaPipe gesture datasets usually don't have header names)
            self.df = pd.read_csv(self.file_path, header=None)
            
            if self.df.empty:
                return False, "Dataset is empty.", {}

            total_cols = self.df.shape[1]
            total_samples = self.df.shape[0]

            # In MediaPipe Hands gesture dataset format:
            # First 63 columns are landmark coordinates (x, y, z for 21 joints).
            # Column 63 (64th column) is the Gesture Label string.
            # Column 64 (65th column) is Timestamp (optional).
            # Column 65 (66th column) is Session ID (optional).
            
            # Auto-detect label column:
            # We assume features are numeric and label is string/categorical.
            # Usually, the label is in index 63. Let's find the label column:
            label_col_idx = 63 if total_cols >= 64 else total_cols - 1
            
            # Detect and drop header rows where the label column is 'label' (case-insensitive)
            header_mask = self.df.iloc[:, label_col_idx].astype(str).str.strip().str.lower() == 'label'
            if header_mask.any():
                self.df = self.df[~header_mask].reset_index(drop=True)
                total_samples = self.df.shape[0]

            # Extract features (first 63 columns, or up to label_col_idx)
            self.features = self.df.iloc[:, :label_col_idx].values
            self.labels = self.df.iloc[:, label_col_idx].values

            # Convert features to numeric, force errors to NaN
            features_df = pd.DataFrame(self.features)
            for col in features_df.columns:
                features_df[col] = pd.to_numeric(features_df[col], errors='coerce')
            self.features = features_df.values

            # Count NaNs and missing values
            nan_count = np.isnan(self.features).sum() + pd.isnull(pd.Series(self.labels)).sum()
            missing_val_count = self.df.isnull().sum().sum()

            # Class names and frequencies
            unique_classes, counts = np.unique(self.labels, return_counts=True)
            class_distribution = {str(c): int(cnt) for c, cnt in zip(unique_classes, counts)}

            # Generate stats
            self.stats = {
                "file_path": self.file_path,
                "samples_count": total_samples,
                "features_count": self.features.shape[1],
                "classes_count": len(unique_classes),
                "nan_count": int(nan_count),
                "missing_val_count": int(missing_val_count),
                "class_distribution": class_distribution,
                "class_list": list(map(str, unique_classes))
            }

            return True, "Dataset loaded successfully.", self.stats

        except Exception as e:
            return False, f"Failed to load dataset: {str(e)}", {}

    def get_data(self):
        """
        Returns features X (numpy array) and labels y (numpy array)
        """
        return self.features, self.labels
