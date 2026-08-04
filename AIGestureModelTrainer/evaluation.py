from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
import numpy as np
import sys
import pickle

class Evaluator:
    @staticmethod
    def evaluate_model(model, X_test, y_test):
        """
        Evaluates a trained model on a test set.
        """
        y_pred = model.predict(X_test)
        
        acc = accuracy_score(y_test, y_pred)
        prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
        cm = confusion_matrix(y_test, y_pred)
        rep = classification_report(y_test, y_pred, zero_division=0)
        
        return {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "confusion_matrix": cm,
            "classification_report": rep,
            "predictions": y_pred
        }

    @staticmethod
    def get_model_size_kb(model):
        """
        Estimates the model size in memory when serialized.
        """
        try:
            return len(pickle.dumps(model)) / 1024.0
        except Exception:
            return sys.getsizeof(model) / 1024.0
            
    @staticmethod
    def format_confusion_matrix_text(cm, classes):
        """
        Formats confusion matrix as an easy-to-read text table.
        """
        header = "Confusion Matrix:\n"
        max_len = max(len(c) for c in classes)
        cell_width = max(max_len, 6)
        
        # Header row
        header += " " * (cell_width + 2)
        for c in classes:
            header += f"{c:>{cell_width}} "
        header += "\n"
        
        # Rows
        for i, row_label in enumerate(classes):
            header += f"{row_label:>{cell_width}}: "
            for j, val in enumerate(cm[i]):
                header += f"{val:>{cell_width}} "
            header += "\n"
            
        return header
