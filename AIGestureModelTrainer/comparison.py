import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from sklearn.model_selection import learning_curve

class ModelComparison:
    def __init__(self, all_results):
        """
        all_results: dict containing model name -> results_dict from trainer.py
        """
        self.results = all_results
        self.comparison_df = self.build_comparison_table()

    def build_comparison_table(self):
        """
        Builds a pandas DataFrame comparing all trained models.
        """
        rows = []
        for model_name, res in self.results.items():
            rows.append({
                "Model": model_name,
                "Accuracy (%)": round(res["accuracy"] * 100, 2),
                "Precision (%)": round(res["precision"] * 100, 2),
                "Recall (%)": round(res["recall"] * 100, 2),
                "F1 Score (%)": round(res["f1"] * 100, 2),
                "Training Time (s)": round(res["train_time"], 4),
                "Prediction Time (s)": round(res["pred_time"], 4),
                "Memory Usage (KB)": round(res["memory_usage"], 2)
            })
        return pd.DataFrame(rows)

    def get_comparison_table(self):
        return self.comparison_df

    @staticmethod
    def plot_metric_comparison(fig, results):
        """
        Plots a grouped bar chart comparing Accuracy and F1 Score of all models.
        """
        fig.clear()
        ax = fig.add_subplot(111)
        
        models = list(results.keys())
        accuracies = [results[m]["accuracy"] * 100 for m in models]
        f1s = [results[m]["f1"] * 100 for m in models]
        
        x = np.arange(len(models))
        width = 0.35
        
        # Modern dark theme styles
        fig.patch.set_facecolor('#1A1A1A')
        ax.set_facecolor('#262626')
        ax.tick_params(colors='#E0E0E0')
        ax.xaxis.label.set_color('#E0E0E0')
        ax.yaxis.label.set_color('#E0E0E0')
        ax.title.set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#444444')
        ax.spines['top'].set_color('#444444')
        ax.spines['left'].set_color('#444444')
        ax.spines['right'].set_color('#444444')
        
        rects1 = ax.bar(x - width/2, accuracies, width, label='Accuracy', color='#00E5FF')
        rects2 = ax.bar(x + width/2, f1s, width, label='F1 Score', color='#8A2BE2')
        
        ax.set_ylabel('Percentage (%)', fontsize=10)
        ax.set_title('Accuracy and F1 Score Comparison', fontsize=12, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=15, ha='right', fontsize=9)
        ax.legend(facecolor='#1A1A1A', labelcolor='#E0E0E0', edgecolor='#444444')
        
        # Add values on top of bars
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.1f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=8, color='#E0E0E0')
                            
        autolabel(rects1)
        autolabel(rects2)
        
        ax.set_ylim(0, 115)
        fig.tight_layout()

    @staticmethod
    def plot_time_comparison(fig, results):
        """
        Plots a bar chart comparing the training time of all models.
        """
        fig.clear()
        ax = fig.add_subplot(111)
        
        models = list(results.keys())
        times = [results[m]["train_time"] for m in models]
        
        fig.patch.set_facecolor('#1A1A1A')
        ax.set_facecolor('#262626')
        ax.tick_params(colors='#E0E0E0')
        ax.xaxis.label.set_color('#E0E0E0')
        ax.yaxis.label.set_color('#E0E0E0')
        ax.title.set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#444444')
        ax.spines['top'].set_color('#444444')
        ax.spines['left'].set_color('#444444')
        ax.spines['right'].set_color('#444444')
        
        colors = ['#FF5252', '#FFD700', '#4CAF50', '#00E5FF', '#9C27B0', '#FF9800']
        rects = ax.bar(models, times, color=colors[:len(models)], width=0.5)
        
        ax.set_ylabel('Training Time (seconds)', fontsize=10)
        ax.set_title('Training Time Comparison (lower is better)', fontsize=12, fontweight='bold', pad=15)
        ax.set_xticklabels(models, rotation=15, ha='right', fontsize=9)
        
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.3f}s',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8, color='#E0E0E0')
                        
        fig.tight_layout()

    @staticmethod
    def plot_feature_importance(fig, results, model_name):
        """
        Plots the top 15 features by importance.
        """
        fig.clear()
        ax = fig.add_subplot(111)
        
        fig.patch.set_facecolor('#1A1A1A')
        ax.set_facecolor('#262626')
        ax.tick_params(colors='#E0E0E0')
        ax.xaxis.label.set_color('#E0E0E0')
        ax.yaxis.label.set_color('#E0E0E0')
        ax.title.set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#444444')
        ax.spines['top'].set_color('#444444')
        ax.spines['left'].set_color('#444444')
        ax.spines['right'].set_color('#444444')

        if model_name not in results or results[model_name].get("feature_importances") is None:
            ax.text(0.5, 0.5, "Feature Importances not available\n(Select Random Forest, Decision Tree or Logistic Regression)", 
                    ha='center', va='center', color='#888888', fontsize=10)
            return

        importances = results[model_name]["feature_importances"]
        num_features = len(importances)
        
        # Map indices to landmark name descriptions if there are 63 columns
        # Each landmark has 3 components: x, y, z
        landmark_names = [
            "WRIST", "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
            "INDEX_FINGER_MCP", "INDEX_FINGER_PIP", "INDEX_FINGER_DIP", "INDEX_FINGER_TIP",
            "MIDDLE_FINGER_MCP", "MIDDLE_FINGER_PIP", "MIDDLE_FINGER_DIP", "MIDDLE_FINGER_TIP",
            "RING_FINGER_MCP", "RING_FINGER_PIP", "RING_FINGER_DIP", "RING_FINGER_TIP",
            "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP"
        ]
        
        feature_labels = []
        for i in range(num_features):
            joint_idx = i // 3
            coord = ["x", "y", "z"][i % 3]
            if joint_idx < len(landmark_names):
                feature_labels.append(f"{landmark_names[joint_idx]}_{coord} (col {i})")
            else:
                feature_labels.append(f"Feature_{i}")
                
        # Get top 15
        indices = np.argsort(importances)[::-1][:15]
        top_importances = importances[indices]
        top_labels = [feature_labels[idx] for idx in indices]
        
        # Plot
        y_pos = np.arange(len(top_labels))
        ax.barh(y_pos, top_importances, align='center', color='#00E5FF')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_labels, fontsize=8)
        ax.invert_yaxis()  # top-down
        ax.set_xlabel('Relative Importance', fontsize=10)
        ax.set_title(f'Top 15 Features for {model_name}', fontsize=12, fontweight='bold', pad=15)
        
        fig.tight_layout()

    @staticmethod
    def plot_learning_curve(fig, results, model_name, X, y, cv=3):
        """
        Plots the learning curve for a model.
        """
        fig.clear()
        ax = fig.add_subplot(111)
        
        fig.patch.set_facecolor('#1A1A1A')
        ax.set_facecolor('#262626')
        ax.tick_params(colors='#E0E0E0')
        ax.xaxis.label.set_color('#E0E0E0')
        ax.yaxis.label.set_color('#E0E0E0')
        ax.title.set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#444444')
        ax.spines['top'].set_color('#444444')
        ax.spines['left'].set_color('#444444')
        ax.spines['right'].set_color('#444444')
        
        if model_name not in results:
            ax.text(0.5, 0.5, "Train the model first to display learning curve.", 
                    ha='center', va='center', color='#888888', fontsize=10)
            return
            
        model = results[model_name]["model_object"]
        scaler = results[model_name]["scaler_object"]
        
        # Scale X if scaler exists
        if scaler is not None:
            X = scaler.transform(X)
            
        # Draw text showing loading (since learning curve takes time)
        ax.text(0.5, 0.5, "Generating Learning Curve...", ha='center', va='center', color='#00E5FF', fontsize=12)
        fig.canvas.draw()
        
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor('#262626')
        
        # Compute learning curve
        # Keep train_sizes small so it loads faster
        train_sizes = np.linspace(0.1, 1.0, 5)
        train_sizes, train_scores, test_scores = learning_curve(
            model, X, y, cv=cv, train_sizes=train_sizes, scoring='accuracy', n_jobs=-1
        )
        
        train_scores_mean = np.mean(train_scores, axis=1)
        train_scores_std = np.std(train_scores, axis=1)
        test_scores_mean = np.mean(test_scores, axis=1)
        test_scores_std = np.std(test_scores, axis=1)
        
        ax.fill_between(train_sizes, train_scores_mean - train_scores_std,
                         train_scores_mean + train_scores_std, alpha=0.1, color="#00E5FF")
        ax.fill_between(train_sizes, test_scores_mean - test_scores_std,
                         test_scores_mean + test_scores_std, alpha=0.1, color="#8A2BE2")
                         
        ax.plot(train_sizes, train_scores_mean, 'o-', color="#00E5FF", label="Training score")
        ax.plot(train_sizes, test_scores_mean, 'o-', color="#8A2BE2", label="Cross-validation score")
        
        ax.set_xlabel("Training samples", fontsize=10)
        ax.set_ylabel("Accuracy Score", fontsize=10)
        ax.set_title(f"Learning Curve for {model_name}", fontsize=12, fontweight='bold', pad=15)
        ax.legend(facecolor='#1A1A1A', labelcolor='#E0E0E0', edgecolor='#444444')
        ax.grid(True, color="#444444", linestyle="--", alpha=0.5)
        
        fig.tight_layout()
