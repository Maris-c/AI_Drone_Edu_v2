from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np

class Preprocessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.is_scaled = False

    def split_dataset(self, X, y, test_size=0.2, shuffle=True, random_state=42):
        """
        Splits the dataset into training and testing sets using a Stratified split.
        """
        # Clean missing/NaN features if any, by imputing with mean or dropping.
        # Since this is gesture landmarks, we can replace any NaN with 0.0 (or mean).
        # We will check if there are NaNs and fill them.
        if np.isnan(X).any():
            col_means = np.nanmean(X, axis=0)
            # Find indices where nan exists
            inds = np.where(np.isnan(X))
            # Place column mean in the nan spots
            X[inds] = np.take(col_means, inds[1])

        # Stratified split ensures class ratios are preserved in train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            shuffle=shuffle,
            stratify=y,
            random_state=random_state
        )
        return X_train, X_test, y_train, y_test

    def check_balance(self, y):
        """
        Checks the balance of the dataset.
        Returns a tuple: (is_balanced, balance_ratio_summary)
        """
        unique, counts = np.unique(y, return_counts=True)
        min_cnt = np.min(counts)
        max_cnt = np.max(counts)
        
        # If ratio of smallest class to largest class is less than 0.5, it's considered imbalanced
        ratio = min_cnt / max_cnt if max_cnt > 0 else 0
        is_balanced = ratio >= 0.5
        
        summary = f"Class counts range from {min_cnt} to {max_cnt} (Ratio: {ratio:.2f})"
        return is_balanced, ratio, summary

    def fit_transform(self, X_train):
        """
        Fits the StandardScaler on X_train and returns scaled X_train.
        """
        self.is_scaled = True
        return self.scaler.fit_transform(X_train)

    def transform(self, X_test):
        """
        Transforms X_test using the fitted StandardScaler.
        """
        if not self.is_scaled:
            raise ValueError("Scaler has not been fitted yet. Call fit_transform first.")
        return self.scaler.transform(X_test)

    def get_scaler(self):
        return self.scaler
