import os
import sys
import time
import cv2
import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QTabWidget, QGroupBox,
    QRadioButton, QProgressBar, QTextEdit, QComboBox, QCheckBox, QFrame,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont, QColor

from tester_engine import ModelTesterEngine
from pdf_report import PDFReportGenerator

# --- Dark Theme CSS Stylesheet ---
DARK_THEME_STYLE = """
QMainWindow {
    background-color: #0F172A;
}
QWidget {
    color: #F8FAFC;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #1E293B;
    background-color: #0F172A;
    border-radius: 8px;
}
QTabBar::tab {
    background: #1E293B;
    color: #94A3B8;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #3B82F6;
    color: #FFFFFF;
}
QTabBar::tab:hover:!selected {
    background: #334155;
    color: #F8FAFC;
}
QGroupBox {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    padding: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #38BDF8;
}
QLineEdit {
    background-color: #0F172A;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
}
QLineEdit:focus {
    border: 1px solid #3B82F6;
}
QPushButton {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2563EB;
}
QPushButton:pressed {
    background-color: #1D4ED8;
}
QPushButton:disabled {
    background-color: #475569;
    color: #94A3B8;
}
QPushButton#btn_secondary {
    background-color: #334155;
    color: #F8FAFC;
}
QPushButton#btn_secondary:hover {
    background-color: #475569;
}
QPushButton#btn_export {
    background-color: #10B981;
}
QPushButton#btn_export:hover {
    background-color: #059669;
}
QPushButton#btn_webcam_start {
    background-color: #10B981;
}
QPushButton#btn_webcam_stop {
    background-color: #EF4444;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    background-color: #0F172A;
}
QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 5px;
}
QTextEdit {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    color: #E2E8F0;
}
QTableWidget {
    background-color: #0F172A;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 6px;
}
QHeaderView::section {
    background-color: #1E293B;
    color: #38BDF8;
    padding: 6px;
    font-weight: bold;
    border: none;
}
"""

class EvaluationWorker(QThread):
    progress_signal = Signal(int)
    finished_signal = Signal(bool, str, dict)

    def __init__(self, engine, dataset_path):
        super().__init__()
        self.engine = engine
        self.dataset_path = dataset_path

    def run(self):
        def progress_cb(pct):
            self.progress_signal.emit(pct)

        success, msg, metrics = self.engine.evaluate_dataset(
            self.dataset_path, progress_callback=progress_cb
        )
        self.finished_signal.emit(success, msg, metrics)

class WebcamThread(QThread):
    frame_signal = Signal(object, str, float, bool, float)

    def __init__(self, engine, camera_index=0):
        super().__init__()
        self.engine = engine
        self.camera_index = camera_index
        self.running = False
        self.flip_horizontal = True

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True

        while self.running:
            ret, frame = cap.read()
            if not ret:
                break

            if self.flip_horizontal:
                frame = cv2.flip(frame, 1)

            annotated_frame, gesture_name, confidence, detected, latency_ms = self.engine.process_frame(frame)
            self.frame_signal.emit(annotated_frame, gesture_name, confidence, detected, latency_ms)
            time.sleep(0.01)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()

class MetricCard(QFrame):
    def __init__(self, title, initial_value="--", accent_color="#3B82F6"):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1E293B;
                border: 1px solid #334155;
                border-left: 4px solid {accent_color};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        
        self.lbl_value = QLabel(initial_value)
        self.lbl_value.setStyleSheet(f"color: #F8FAFC; font-size: 18px; font-weight: bold;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def set_value(self, value_text, color=None):
        self.lbl_value.setText(value_text)
        if color:
            self.lbl_value.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")

class GestureTesterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Drone - MediaPipe Model Tester & Reliability Evaluator")
        self.resize(1100, 750)
        self.setStyleSheet(DARK_THEME_STYLE)

        self.engine = ModelTesterEngine()
        self.latest_metrics = None
        self.webcam_thread = None

        self.init_ui()
        self.auto_load_default_paths()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header Title Banner
        header_layout = QHBoxLayout()
        lbl_title = QLabel("AI DRONE GESTURE MODEL TESTER & PARAMETER EVALUATOR")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: #38BDF8;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Main Tab Widget
        self.tabs = QTabWidget()
        self.tab_benchmark = QWidget()
        self.tab_webcam = QWidget()

        self.tabs.addTab(self.tab_benchmark, "Benchmark & Model Metrics")
        self.tabs.addTab(self.tab_webcam, "Live Webcam Tester")

        main_layout.addWidget(self.tabs)

        self.setup_benchmark_tab()
        self.setup_webcam_tab()

    def auto_load_default_paths(self):
        """Auto-detects model and landmarker task paths if present."""
        if os.path.exists(self.engine.model_path):
            self.txt_model_path.setText(self.engine.model_path)
        if os.path.exists(self.engine.scaler_path):
            self.txt_scaler_path.setText(self.engine.scaler_path)
        if os.path.exists(self.engine.task_path):
            self.txt_task_path.setText(self.engine.task_path)

        # Auto-fill dataset directory if present
        default_ds = os.path.join(os.path.dirname(self.engine.app_dir), "dataset")
        if os.path.exists(default_ds):
            self.txt_dataset_path.setText(default_ds)

    def setup_benchmark_tab(self):
        layout = QHBoxLayout(self.tab_benchmark)

        # Left Control Panel
        left_panel = QWidget()
        left_panel.setFixedWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Model Config Group
        group_model = QGroupBox("Model & Classifier Setup")
        g_model_layout = QVBoxLayout(group_model)

        g_model_layout.addWidget(QLabel("Model Path (.pkl / .joblib):"))
        h_mod = QHBoxLayout()
        self.txt_model_path = QLineEdit()
        btn_mod = QPushButton("Browse")
        btn_mod.setObjectName("btn_secondary")
        btn_mod.clicked.connect(self.browse_model_path)
        h_mod.addWidget(self.txt_model_path)
        h_mod.addWidget(btn_mod)
        g_model_layout.addLayout(h_mod)

        g_model_layout.addWidget(QLabel("Scaler Path (scaler.pkl):"))
        h_scl = QHBoxLayout()
        self.txt_scaler_path = QLineEdit()
        btn_scl = QPushButton("Browse")
        btn_scl.setObjectName("btn_secondary")
        btn_scl.clicked.connect(self.browse_scaler_path)
        h_scl.addWidget(self.txt_scaler_path)
        h_scl.addWidget(btn_scl)
        g_model_layout.addLayout(h_scl)

        g_model_layout.addWidget(QLabel("Hand Landmarker Task:"))
        h_tsk = QHBoxLayout()
        self.txt_task_path = QLineEdit()
        btn_tsk = QPushButton("Browse")
        btn_tsk.setObjectName("btn_secondary")
        btn_tsk.clicked.connect(self.browse_task_path)
        h_tsk.addWidget(self.txt_task_path)
        h_tsk.addWidget(btn_tsk)
        g_model_layout.addLayout(h_tsk)

        left_layout.addWidget(group_model)

        # Test Dataset Group
        group_ds = QGroupBox("Test Dataset Configuration")
        g_ds_layout = QVBoxLayout(group_ds)

        self.radio_folder = QRadioButton("Image Folder (Class subfolders)")
        self.radio_csv = QRadioButton("CSV Landmark File (.csv)")
        self.radio_folder.setChecked(True)

        g_ds_layout.addWidget(self.radio_folder)
        g_ds_layout.addWidget(self.radio_csv)

        g_ds_layout.addWidget(QLabel("Dataset Path:"))
        h_ds = QHBoxLayout()
        self.txt_dataset_path = QLineEdit()
        btn_ds = QPushButton("Browse")
        btn_ds.setObjectName("btn_secondary")
        btn_ds.clicked.connect(self.browse_dataset_path)
        h_ds.addWidget(self.txt_dataset_path)
        h_ds.addWidget(btn_ds)
        g_ds_layout.addLayout(h_ds)

        left_layout.addWidget(group_ds)

        # Action Buttons & Progress
        self.btn_run_eval = QPushButton("RUN MODEL EVALUATION")
        self.btn_run_eval.setFixedHeight(40)
        self.btn_run_eval.clicked.connect(self.run_evaluation)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.btn_export_pdf = QPushButton("EXPORT PDF REPORT")
        self.btn_export_pdf.setObjectName("btn_export")
        self.btn_export_pdf.setFixedHeight(38)
        self.btn_export_pdf.setEnabled(False)
        self.btn_export_pdf.clicked.connect(self.export_pdf_report)

        left_layout.addWidget(self.btn_run_eval)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.btn_export_pdf)
        left_layout.addStretch()

        layout.addWidget(left_panel)

        # Right Dashboard Results Panel
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Rating Grade Banner
        self.card_rating = QFrame()
        self.card_rating.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 2px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        r_layout = QVBoxLayout(self.card_rating)
        self.lbl_rating_title = QLabel("MODEL RELIABILITY RATING: NOT EVALUATED YET")
        self.lbl_rating_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.lbl_rating_title.setStyleSheet("color: #94A3B8;")

        self.lbl_rating_desc = QLabel("Click 'RUN MODEL EVALUATION' to test dataset and obtain reliability metrics.")
        self.lbl_rating_desc.setStyleSheet("color: #CBD5E1; font-size: 12px;")
        self.lbl_rating_desc.setWordWrap(True)

        r_layout.addWidget(self.lbl_rating_title)
        r_layout.addWidget(self.lbl_rating_desc)
        right_layout.addWidget(self.card_rating)

        # Metric Cards Grid
        grid_metrics = QGridLayout()
        self.card_acc = MetricCard("ACCURACY", "--", "#10B981")
        self.card_prec = MetricCard("PRECISION", "--", "#3B82F6")
        self.card_rec = MetricCard("RECALL", "--", "#8B5CF6")
        self.card_f1 = MetricCard("F1-SCORE", "--", "#F59E0B")
        self.card_det = MetricCard("DETECTION RATE", "--", "#06B6D4")
        self.card_fps = MetricCard("LATENCY / FPS", "--", "#EC4899")

        grid_metrics.addWidget(self.card_acc, 0, 0)
        grid_metrics.addWidget(self.card_prec, 0, 1)
        grid_metrics.addWidget(self.card_rec, 0, 2)
        grid_metrics.addWidget(self.card_f1, 1, 0)
        grid_metrics.addWidget(self.card_det, 1, 1)
        grid_metrics.addWidget(self.card_fps, 1, 2)

        right_layout.addLayout(grid_metrics)

        # Confusion Matrix Matplotlib Canvas
        group_cm = QGroupBox("Confusion Matrix Visualization")
        g_cm_layout = QVBoxLayout(group_cm)

        self.fig_cm = Figure(figsize=(5, 3.5), facecolor='#1E293B')
        self.canvas_cm = FigureCanvas(self.fig_cm)
        g_cm_layout.addWidget(self.canvas_cm)

        right_layout.addWidget(group_cm)

        # Classification Report Text
        group_rep = QGroupBox("Detailed Classification Report")
        g_rep_layout = QVBoxLayout(group_rep)
        self.txt_clf_report = QTextEdit()
        self.txt_clf_report.setReadOnly(True)
        self.txt_clf_report.setFixedHeight(140)
        g_rep_layout.addWidget(self.txt_clf_report)

        right_layout.addWidget(group_rep)

        right_scroll.setWidget(right_widget)
        layout.addWidget(right_scroll)

    def setup_webcam_tab(self):
        layout = QHBoxLayout(self.tab_webcam)

        # Left Video Stream Display
        v_left = QVBoxLayout()
        self.lbl_video = QLabel("Webcam Feed Offline")
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setMinimumSize(640, 480)
        self.lbl_video.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 2px solid #1E293B;
                border-radius: 8px;
                color: #64748B;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        v_left.addWidget(self.lbl_video)

        # Webcam Control Bar
        h_ctrl = QHBoxLayout()
        h_ctrl.addWidget(QLabel("Camera Index:"))
        self.combo_cam = QComboBox()
        self.combo_cam.addItems(["0", "1", "2"])
        h_ctrl.addWidget(self.combo_cam)

        self.chk_flip = QCheckBox("Flip Mirror")
        self.chk_flip.setChecked(True)
        h_ctrl.addWidget(self.chk_flip)

        self.btn_webcam_toggle = QPushButton("START WEBCAM")
        self.btn_webcam_toggle.setObjectName("btn_webcam_start")
        self.btn_webcam_toggle.clicked.connect(self.toggle_webcam)
        h_ctrl.addWidget(self.btn_webcam_toggle)

        v_left.addLayout(h_ctrl)
        layout.addLayout(v_left)

        # Right Live Metrics Panel
        v_right = QVBoxLayout()
        
        group_live = QGroupBox("Live Prediction HUD")
        g_live_layout = QVBoxLayout(group_live)

        self.lbl_live_gesture = QLabel("NO HAND")
        self.lbl_live_gesture.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.lbl_live_gesture.setStyleSheet("color: #10B981; padding: 10px;")
        self.lbl_live_gesture.setAlignment(Qt.AlignCenter)

        self.lbl_live_conf = QLabel("Confidence: 0.0%")
        self.lbl_live_conf.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        self.lbl_live_conf.setAlignment(Qt.AlignCenter)

        self.lbl_live_fps = QLabel("FPS: 0.0 | Latency: 0.0 ms")
        self.lbl_live_fps.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.lbl_live_fps.setAlignment(Qt.AlignCenter)

        g_live_layout.addWidget(self.lbl_live_gesture)
        g_live_layout.addWidget(self.lbl_live_conf)
        g_live_layout.addWidget(self.lbl_live_fps)

        v_right.addWidget(group_live)

        # History Table
        group_hist = QGroupBox("Live Detection History Log")
        g_hist_layout = QVBoxLayout(group_hist)

        self.tbl_history = QTableWidget(0, 3)
        self.tbl_history.setHorizontalHeaderLabels(["Timestamp", "Gesture", "Confidence"])
        self.tbl_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        g_hist_layout.addWidget(self.tbl_history)

        v_right.addWidget(group_hist)

        layout.addLayout(v_right)

    # --- File Browsing Slots ---
    def browse_model_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Classifier Model", "", "Model Files (*.pkl *.joblib)")
        if path:
            self.txt_model_path.setText(path)

    def browse_scaler_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Scaler", "", "Scaler Files (*.pkl *.joblib)")
        if path:
            self.txt_scaler_path.setText(path)

    def browse_task_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Hand Landmarker Task", "", "Task Files (*.task)")
        if path:
            self.txt_task_path.setText(path)

    def browse_dataset_path(self):
        if self.radio_csv.isChecked():
            path, _ = QFileDialog.getOpenFileName(self, "Select Test CSV File", "", "CSV Files (*.csv)")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Test Image Directory")
        if path:
            self.txt_dataset_path.setText(path)

    # --- Benchmark Evaluation Execution ---
    def run_evaluation(self):
        model_path = self.txt_model_path.text().strip()
        scaler_path = self.txt_scaler_path.text().strip()
        task_path = self.txt_task_path.text().strip()
        ds_path = self.txt_dataset_path.text().strip()

        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(self, "Error", "Please select a valid model .pkl file.")
            return

        if not ds_path or not os.path.exists(ds_path):
            QMessageBox.warning(self, "Error", "Please select a valid test dataset path.")
            return

        # Load engine options
        self.engine.model_path = model_path
        self.engine.scaler_path = scaler_path if scaler_path else None
        self.engine.task_path = task_path if task_path else self.engine.task_path

        success, msg = self.engine.load_model()
        if not success:
            QMessageBox.critical(self, "Model Loading Failed", msg)
            return

        self.btn_run_eval.setEnabled(False)
        self.progress_bar.setValue(0)

        # Worker Thread
        self.worker = EvaluationWorker(self.engine, ds_path)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_evaluation_finished)
        self.worker.start()

    def on_evaluation_finished(self, success, msg, metrics):
        self.btn_run_eval.setEnabled(True)
        if not success:
            QMessageBox.critical(self, "Evaluation Error", msg)
            return

        self.latest_metrics = metrics
        self.btn_export_pdf.setEnabled(True)

        # Update Rating Card
        grade = metrics.get("rating_grade", "N/A")
        desc = metrics.get("rating_text", "")
        hex_color = metrics.get("rating_color", "#3B82F6")

        self.card_rating.setStyleSheet(f"""
            QFrame {{
                background-color: #1E293B;
                border: 2px solid {hex_color};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        self.lbl_rating_title.setText(f"RATING: {grade}")
        self.lbl_rating_title.setStyleSheet(f"color: {hex_color}; font-size: 15px; font-weight: bold;")
        self.lbl_rating_desc.setText(desc)

        # Update Metric Cards
        self.card_acc.set_value(f"{metrics['accuracy']*100:.1f}%", hex_color)
        self.card_prec.set_value(f"{metrics['precision']*100:.1f}%")
        self.card_rec.set_value(f"{metrics['recall']*100:.1f}%")
        self.card_f1.set_value(f"{metrics['f1_score']*100:.1f}%")
        self.card_det.set_value(f"{metrics['detection_rate']:.1f}%")
        self.card_fps.set_value(f"{metrics['avg_latency_ms']:.1f} ms ({metrics['fps']:.1f} FPS)")

        # Render Confusion Matrix
        self.render_confusion_matrix(metrics['confusion_matrix'], metrics['classes'])

        # Update Text Classification Report
        self.txt_clf_report.setPlainText(metrics['classification_report'])

        QMessageBox.information(self, "Success", "Model evaluation completed successfully!")

    def render_confusion_matrix(self, cm, classes):
        self.fig_cm.clear()
        ax = self.fig_cm.add_subplot(111)
        ax.set_facecolor('#1E293B')

        im = ax.imshow(cm, interpolation='nearest', cmap=matplotlib.cm.Blues)
        self.fig_cm.colorbar(im, ax=ax)

        tick_marks = np.arange(len(classes))
        ax.set_xticks(tick_marks)
        ax.set_xticklabels(classes, rotation=45, ha='right', color='#F8FAFC', fontsize=8)
        ax.set_yticks(tick_marks)
        ax.set_yticklabels(classes, color='#F8FAFC', fontsize=8)

        thresh = cm.max() / 2.0 if cm.max() > 0 else 1.0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                val = cm[i, j]
                ax.text(j, i, f"{val}", horizontalalignment="center",
                        color="white" if val > thresh else "black", fontsize=8, fontweight='bold')

        ax.set_ylabel('True Class', color='#38BDF8', fontsize=9, fontweight='bold')
        ax.set_xlabel('Predicted Class', color='#38BDF8', fontsize=9, fontweight='bold')
        self.fig_cm.tight_layout()
        self.canvas_cm.draw()

    # --- Export PDF Report ---
    def export_pdf_report(self):
        if not self.latest_metrics:
            return

        default_name = os.path.join(self.engine.app_dir, "model_reliability_report.pdf")
        save_path, _ = QFileDialog.getSaveFileName(self, "Export Evaluation PDF Report", default_name, "PDF Files (*.pdf)")
        if save_path:
            try:
                pdf_gen = PDFReportGenerator(self.latest_metrics)
                success, msg = pdf_gen.generate_pdf(save_path)
                if success:
                    QMessageBox.information(self, "Report Saved", f"PDF evaluation report exported to:\n{save_path}")
                else:
                    QMessageBox.critical(self, "PDF Export Error", msg)
            except Exception as e:
                QMessageBox.critical(self, "PDF Export Exception", str(e))

    # --- Real-time Webcam Tester Slots ---
    def toggle_webcam(self):
        if self.webcam_thread is not None and self.webcam_thread.running:
            # Stop
            self.webcam_thread.stop()
            self.webcam_thread = None
            self.btn_webcam_toggle.setText("START WEBCAM")
            self.btn_webcam_toggle.setObjectName("btn_webcam_start")
            self.btn_webcam_toggle.setStyle(self.btn_webcam_toggle.style())
            self.lbl_video.setText("Webcam Feed Offline")
        else:
            # Ensure model loaded
            model_path = self.txt_model_path.text().strip()
            scaler_path = self.txt_scaler_path.text().strip()
            task_path = self.txt_task_path.text().strip()

            self.engine.model_path = model_path if model_path else self.engine.model_path
            self.engine.scaler_path = scaler_path if scaler_path else None
            self.engine.task_path = task_path if task_path else self.engine.task_path

            success, msg = self.engine.load_model()
            if not success:
                QMessageBox.warning(self, "Model Required", f"Please select and load a valid model first: {msg}")
                return

            cam_idx = int(self.combo_cam.currentText())
            self.webcam_thread = WebcamThread(self.engine, camera_index=cam_idx)
            self.webcam_thread.flip_horizontal = self.chk_flip.isChecked()
            self.webcam_thread.frame_signal.connect(self.update_webcam_frame)
            self.webcam_thread.start()

            self.btn_webcam_toggle.setText("STOP WEBCAM")
            self.btn_webcam_toggle.setObjectName("btn_webcam_stop")
            self.btn_webcam_toggle.setStyle(self.btn_webcam_toggle.style())

    def update_webcam_frame(self, frame_bgr, gesture_name, confidence, detected, latency_ms):
        # Convert BGR to QImage
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.lbl_video.setPixmap(pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Update Live HUD
        if detected:
            self.lbl_live_gesture.setText(gesture_name)
            self.lbl_live_gesture.setStyleSheet("color: #10B981; font-size: 22px; font-weight: bold;")
            self.lbl_live_conf.setText(f"Confidence: {confidence:.1f}%")
        else:
            self.lbl_live_gesture.setText("NO HAND")
            self.lbl_live_gesture.setStyleSheet("color: #64748B; font-size: 22px; font-weight: bold;")
            self.lbl_live_conf.setText("Searching for hand...")

        fps = (1000.0 / latency_ms) if latency_ms > 0 else 0.0
        self.lbl_live_fps.setText(f"FPS: {fps:.1f} | Latency: {latency_ms:.1f} ms")

        # Update History Table
        if detected and gesture_name != "No Hand Detected":
            t_str = time.strftime("%H:%M:%S")
            self.tbl_history.insertRow(0)
            self.tbl_history.setItem(0, 0, QTableWidgetItem(t_str))
            self.tbl_history.setItem(0, 1, QTableWidgetItem(gesture_name))
            self.tbl_history.setItem(0, 2, QTableWidgetItem(f"{confidence:.1f}%"))
            if self.tbl_history.rowCount() > 30:
                self.tbl_history.removeRow(30)

    def closeEvent(self, event):
        if self.webcam_thread is not None and self.webcam_thread.running:
            self.webcam_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GestureTesterWindow()
    window.show()
    sys.exit(app.exec())
