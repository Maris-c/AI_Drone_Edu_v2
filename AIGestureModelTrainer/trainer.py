from PySide6.QtCore import QThread, Signal
import time
import sys
import pickle
import numpy as np

# ML Libraries
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler

class ModelTrainingWorker(QThread):
    # Signals for communicating with UI
    log_signal = Signal(str)
    progress_signal = Signal(int)
    model_trained_signal = Signal(str, dict)  # model_name, results_dict
    finished_signal = Signal(dict, str)       # all_results, best_model_name
    error_signal = Signal(str)

    def __init__(self, X_train, X_test, y_train, y_test, selected_models, settings):
        super().__init__()
        self.X_train = X_train
        self.X_test = X_test
        self.y_train = y_train
        self.y_test = y_test
        self.selected_models = selected_models
        self.settings = settings  # dict containing: ratio, seed, cv_folds, normalize, shuffle
        self.is_running = True

    def stop(self):
        self.is_running = False

    def get_model_instance(self, name):
        seed = self.settings.get("seed", 42)
        if name == "Random Forest":
            return RandomForestClassifier(n_estimators=100, random_state=seed)
        elif name == "Support Vector Machine":
            return SVC(kernel='rbf', C=1.0, probability=True, random_state=seed)
        elif name == "MLP Neural Network":
            return MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=seed)
        elif name == "K-Nearest Neighbor":
            return KNeighborsClassifier(n_neighbors=5)
        elif name == "Decision Tree":
            return DecisionTreeClassifier(max_depth=10, random_state=seed)
        elif name == "Logistic Regression":
            return LogisticRegression(max_iter=1000, random_state=seed)
        else:
            raise ValueError(f"Unknown model name: {name}")

    def run(self):
        try:
            self.log_signal.emit("Starting Training Pipeline...")
            self.progress_signal.emit(5)
            
            results = {}
            best_acc = -1.0
            best_model_name = ""

            total_models = len(self.selected_models)
            if total_models == 0:
                self.error_signal.emit("No models selected for training.")
                return

            for i, model_name in enumerate(self.selected_models):
                if not self.is_running:
                    self.log_signal.emit("Training stopped by user.")
                    break

                self.log_signal.emit(f"--------------------------------------------------")
                self.log_signal.emit(f"Training Model {i+1}/{total_models}: {model_name}...")
                
                # Check if this algorithm requires normalization
                # Based on user instruction: RF, DT don't normalize. SVM, MLP, KNN do.
                # Let's check settings.get("normalize") as a override too.
                needs_normalize = model_name in ["Support Vector Machine", "MLP Neural Network", "K-Nearest Neighbor", "Logistic Regression"]
                
                # Apply normalization if algorithm needs it
                X_tr = self.X_train.copy()
                X_te = self.X_test.copy()
                scaler = None

                if needs_normalize:
                    self.log_signal.emit(f"[{model_name}] Normalizing features using StandardScaler...")
                    scaler = StandardScaler()
                    X_tr = scaler.fit_transform(X_tr)
                    X_te = scaler.transform(X_te)
                else:
                    self.log_signal.emit(f"[{model_name}] Normalization skipped (tree-based algorithm).")

                # Instantiate model
                model = self.get_model_instance(model_name)

                # Cross-Validation Score
                cv_folds = self.settings.get("cv_folds", 5)
                self.log_signal.emit(f"[{model_name}] Running {cv_folds}-Fold Stratified Cross Validation...")
                
                start_cv = time.time()
                skf = StratifiedKFold(n_splits=cv_folds, shuffle=self.settings.get("shuffle", True), random_state=self.settings.get("seed", 42))
                # Compute CV score
                cv_scores = cross_val_score(model, X_tr, self.y_train, cv=skf, scoring='accuracy')
                self.log_signal.emit(f"[{model_name}] CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

                # Fit model on the whole train set
                self.log_signal.emit(f"[{model_name}] Fitting model...")
                start_train = time.time()
                model.fit(X_tr, self.y_train)
                train_time = time.time() - start_train
                self.log_signal.emit(f"[{model_name}] Fit completed in {train_time:.4f} seconds.")

                # Prediction speed (Batch and single sample)
                self.log_signal.emit(f"[{model_name}] Evaluating predictions...")
                start_pred = time.time()
                y_pred = model.predict(X_te)
                pred_time = time.time() - start_pred
                
                # Single sample prediction speed
                single_sample = X_te[0:1]
                start_single = time.time()
                for _ in range(100):  # Run 100 times to get stable average
                    _ = model.predict(single_sample)
                single_pred_time = (time.time() - start_single) / 100.0

                # Compute metrics
                from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report
                acc = accuracy_score(self.y_test, y_pred)
                precision, recall, f1, _ = precision_recall_fscore_support(self.y_test, y_pred, average='macro', zero_division=0)
                
                # Confusion Matrix & Classification Report
                cm = confusion_matrix(self.y_test, y_pred)
                cls_report = classification_report(self.y_test, y_pred, zero_division=0)

                # Memory footprint (size in KB when pickled)
                try:
                    mem_size_kb = len(pickle.dumps(model)) / 1024.0
                except Exception:
                    mem_size_kb = sys.getsizeof(model) / 1024.0

                # Collect model results
                model_results = {
                    "accuracy": acc,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "train_time": train_time,
                    "pred_time": pred_time,
                    "single_pred_time": single_pred_time,
                    "memory_usage": mem_size_kb,
                    "cv_scores": cv_scores.tolist(),
                    "confusion_matrix": cm,
                    "classification_report": cls_report,
                    "model_object": model,
                    "scaler_object": scaler,
                    "y_pred": y_pred
                }

                # Feature importances
                if hasattr(model, 'feature_importances_'):
                    model_results["feature_importances"] = model.feature_importances_
                elif hasattr(model, 'coef_'):
                    model_results["feature_importances"] = np.mean(np.abs(model.coef_), axis=0)
                else:
                    model_results["feature_importances"] = None

                results[model_name] = model_results
                
                # Emit intermediate signal
                self.model_trained_signal.emit(model_name, model_results)
                
                # Select best model based on accuracy, with prediction speed and memory footprint as tie-breakers
                is_better = False
                if acc > best_acc:
                    is_better = True
                elif acc == best_acc:
                    current_best_res = results.get(best_model_name) if best_model_name else None
                    if current_best_res:
                        # Tie-breaker 1: Lower single-sample prediction latency
                        if single_pred_time < current_best_res["single_pred_time"]:
                            is_better = True
                        elif single_pred_time == current_best_res["single_pred_time"]:
                            # Tie-breaker 2: Smaller memory footprint
                            if mem_size_kb < current_best_res["memory_usage"]:
                                is_better = True
                    else:
                        is_better = True

                if is_better:
                    best_acc = acc
                    best_model_name = model_name

                # Update progress
                progress = int(5 + ((i + 1) / total_models) * 90)
                self.progress_signal.emit(progress)
            
            if self.is_running:
                self.progress_signal.emit(100)
                self.log_signal.emit(f"--------------------------------------------------")
                self.log_signal.emit(f"Training Complete! Best model: {best_model_name} with {best_acc*100:.2f}% Accuracy.")
                self.finished_signal.emit(results, best_model_name)

        except Exception as e:
            self.error_signal.emit(str(e))
