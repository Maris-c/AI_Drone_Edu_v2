import os
import sys
import time
import matplotlib
matplotlib.use('QtAgg')

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QCheckBox, QComboBox, QSpinBox, QFileDialog,
    QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem, QTabWidget,
    QMessageBox, QGroupBox, QSplitter, QHeaderView, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor, QTextCursor, QIcon

# Import custom modules
from dataset_loader import DatasetLoader
from preprocessing import Preprocessor
from trainer import ModelTrainingWorker
from comparison import ModelComparison
from report_generator import ReportGenerator
from model_manager import ModelManager

# Matplotlib integration
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class MplCanvas(FigureCanvas):
    def __init__(self, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(fig)
        fig.patch.set_facecolor('#1A1A1A')

class GestureTrainerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Gesture Model Trainer")
        self.resize(1300, 850)
        
        # State variables
        self.dataset_loaded = False
        self.X = None
        self.y = None
        self.dataset_stats = {}
        self.trained_results = {}
        self.best_model_name = ""
        self.training_thread = None
        self.log_accumulator = ""

        # Set main layout stylesheet
        self.apply_theme()
        
        # Initialize UI Components
        self.init_ui()
        
        # Log welcome message
        self.log("Welcome to AI Gesture Model Trainer!")
        self.log("Use the 'Browse' button to select a MediaPipe gesture landmark CSV dataset.")

    def apply_theme(self):
        """
        Applies a premium cyber-drone styling to the application interface.
        Uses dark slate background, cyan accent lines, and purple settings indicators.
        """
        qss = """
        QMainWindow {
            background-color: #121212;
        }
        
        QWidget {
            color: #E0E0E0;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }
        
        QGroupBox {
            font-weight: bold;
            font-size: 14px;
            border: 2px solid #2B2B2B;
            border-radius: 8px;
            margin-top: 12px;
            padding: 8px;
            background-color: #1A1A1A;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            color: #00E5FF;
        }
        
        QLabel {
            color: #B0B0B0;
        }
        
        QLabel#TitleLabel {
            color: #00E5FF;
            font-size: 22px;
            font-weight: bold;
            letter-spacing: 1px;
        }
        
        QLabel#SubtitleLabel {
            color: #8A2BE2;
            font-size: 12px;
            font-weight: bold;
        }

        QLineEdit, QSpinBox, QComboBox {
            background-color: #262626;
            border: 1px solid #3E3E3E;
            border-radius: 4px;
            padding: 5px;
            color: #FFFFFF;
            min-height: 22px;
        }
        
        QComboBox::drop-down {
            border: 0px;
        }
        
        QSpinBox::up-button, QSpinBox::down-button {
            width: 15px;
        }

        QPushButton {
            background-color: #2D2D2D;
            color: #E0E0E0;
            border: 1px solid #444444;
            border-radius: 6px;
            padding: 8px 15px;
            font-weight: bold;
            min-height: 18px;
        }
        
        QPushButton:hover {
            background-color: #3D3D3D;
            border-color: #555555;
        }
        
        QPushButton:pressed {
            background-color: #1D1D1D;
        }
        
        QPushButton#BrowseBtn {
            background-color: #00E5FF;
            color: #0C0C0C;
            border: none;
        }
        
        QPushButton#BrowseBtn:hover {
            background-color: #00B8D4;
        }
        
        QPushButton#TrainSelectedBtn {
            background-color: #8A2BE2;
            color: #FFFFFF;
            border: none;
        }
        
        QPushButton#TrainSelectedBtn:hover {
            background-color: #721CC5;
        }
        
        QPushButton#TrainAllBtn {
            background-color: #00E5FF;
            color: #0C0C0C;
            border: none;
        }
        
        QPushButton#TrainAllBtn:hover {
            background-color: #00B8D4;
        }
        
        QPushButton#StopBtn {
            background-color: #FF1744;
            color: #FFFFFF;
            border: none;
        }
        
        QPushButton#StopBtn:hover {
            background-color: #D50000;
        }
        
        QCheckBox {
            spacing: 6px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1px solid #444444;
            border-radius: 3px;
            background-color: #262626;
        }
        
        QCheckBox::indicator:checked {
            background-color: #00E5FF;
            border-color: #00E5FF;
            image: url(checked.png); /* Fallback to solid color if missing */
        }
        
        QTabWidget::pane {
            border: 1px solid #2B2B2B;
            border-radius: 8px;
            background-color: #1A1A1A;
        }
        
        QTabBar::tab {
            background: #252525;
            color: #B0B0B0;
            border: 1px solid #333333;
            border-bottom-color: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected, QTabBar::tab:hover {
            background: #1A1A1A;
            color: #00E5FF;
            border-bottom: 2px solid #00E5FF;
        }

        QTableWidget {
            gridline-color: #2D2D2D;
            background-color: #1A1A1A;
            border: 1px solid #2D2D2D;
            border-radius: 4px;
            color: #FFFFFF;
        }
        
        QHeaderView::section {
            background-color: #262626;
            color: #B0B0B0;
            padding: 5px;
            border: 1px solid #1D1D1D;
            font-weight: bold;
        }
        
        QTableWidget QTableCornerButton::section {
            background-color: #262626;
        }

        QProgressBar {
            border: 1px solid #2D2D2D;
            border-radius: 5px;
            text-align: center;
            background-color: #121212;
            color: #FFFFFF;
            font-weight: bold;
        }
        
        QProgressBar::chunk {
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #8A2BE2, stop:1 #00E5FF);
            border-radius: 5px;
        }
        
        QTextEdit#LogConsole {
            background-color: #0A0A0A;
            color: #00FFCC;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            border: 1px solid #262626;
            border-radius: 6px;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #121212;
            width: 10px;
            margin: 0px 0 0px 0;
        }
        QScrollBar::handle:vertical {
            background: #333333;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #00E5FF;
        }
        """
        self.setStyleSheet(qss)

    def init_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 10, 15, 15)
        main_layout.setSpacing(10)
        
        # Header Banner
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_v_layout = QVBoxLayout()
        title_v_layout.setSpacing(2)
        title_label = QLabel("AI GESTURE MODEL TRAINER")
        title_label.setObjectName("TitleLabel")
        subtitle_label = QLabel("DRONE CONTROL SYSTEM GESTURE RECOGNITION PIPELINE")
        subtitle_label.setObjectName("SubtitleLabel")
        title_v_layout.addWidget(title_label)
        title_v_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(title_v_layout)
        header_layout.addStretch()
        
        # Connection status / Best Model Display badge
        self.best_model_badge = QGroupBox("Best Model Status")
        self.best_model_badge.setMaximumHeight(70)
        badge_layout = QHBoxLayout(self.best_model_badge)
        badge_layout.setContentsMargins(10, 5, 10, 5)
        self.best_model_lbl = QLabel("No trained models yet")
        self.best_model_lbl.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 14px;")
        badge_layout.addWidget(self.best_model_lbl)
        header_layout.addWidget(self.best_model_badge)
        
        main_layout.addWidget(header_widget)
        
        # Horizontal Splitter for responsive sizing
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Panel (Settings & Configurations)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(10)
        
        # Area 1: Dataset Section
        dataset_group = QGroupBox("1. Dataset Loader")
        dataset_grid = QGridLayout(dataset_group)
        dataset_grid.setSpacing(8)
        
        dataset_grid.addWidget(QLabel("Dataset CSV Path:"), 0, 0)
        self.dataset_path_le = QComboBox()
        self.dataset_path_le.setEditable(True)
        self.dataset_path_le.lineEdit().setPlaceholderText("Select or enter dataset CSV path...")
        dataset_grid.addWidget(self.dataset_path_le, 0, 1)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("BrowseBtn")
        self.browse_btn.clicked.connect(self.browse_dataset)
        dataset_grid.addWidget(self.browse_btn, 0, 2)
        
        # Stats layout inside Dataset
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #202020; border-radius: 6px; padding: 5px;")
        stats_grid = QGridLayout(stats_frame)
        stats_grid.setContentsMargins(8, 8, 8, 8)
        
        stats_grid.addWidget(QLabel("Total Samples:"), 0, 0)
        self.lbl_samples = QLabel("0")
        self.lbl_samples.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        stats_grid.addWidget(self.lbl_samples, 0, 1)
        
        stats_grid.addWidget(QLabel("Features Count:"), 0, 2)
        self.lbl_features = QLabel("0")
        self.lbl_features.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        stats_grid.addWidget(self.lbl_features, 0, 3)
        
        stats_grid.addWidget(QLabel("Classes Count:"), 1, 0)
        self.lbl_classes = QLabel("0")
        self.lbl_classes.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        stats_grid.addWidget(self.lbl_classes, 1, 1)
        
        stats_grid.addWidget(QLabel("NaN/Missing:"), 1, 2)
        self.lbl_nan = QLabel("0")
        self.lbl_nan.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        stats_grid.addWidget(self.lbl_nan, 1, 3)
        
        dataset_grid.addWidget(stats_frame, 1, 0, 1, 3)
        
        # Distribution table
        dataset_grid.addWidget(QLabel("Gesture Class Distribution:"), 2, 0, 1, 3)
        self.dist_table = QTableWidget(0, 2)
        self.dist_table.setHorizontalHeaderLabels(["Gesture Label", "Samples Count"])
        self.dist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dist_table.setMaximumHeight(120)
        dataset_grid.addWidget(self.dist_table, 3, 0, 1, 3)
        
        left_layout.addWidget(dataset_group)
        
        # Area 2: Training Settings Section
        settings_group = QGroupBox("2. Training Configuration")
        settings_grid = QGridLayout(settings_group)
        settings_grid.setSpacing(8)
        
        settings_grid.addWidget(QLabel("Train/Test Ratio:"), 0, 0)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["80/20", "70/30", "75/25", "90/10"])
        settings_grid.addWidget(self.ratio_combo, 0, 1)
        
        settings_grid.addWidget(QLabel("Random State Seed:"), 0, 2)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 99999)
        self.seed_spin.setValue(42)
        settings_grid.addWidget(self.seed_spin, 0, 3)
        
        settings_grid.addWidget(QLabel("Cross Validation:"), 1, 0)
        self.cv_combo = QComboBox()
        self.cv_combo.addItems(["5 Folds", "10 Folds", "3 Folds", "2 Folds"])
        settings_grid.addWidget(self.cv_combo, 1, 1)
        
        self.chk_normalize = QCheckBox("Normalize (Auto scaler)")
        self.chk_normalize.setChecked(True)
        settings_grid.addWidget(self.chk_normalize, 1, 2)
        
        self.chk_shuffle = QCheckBox("Shuffle Dataset")
        self.chk_shuffle.setChecked(True)
        settings_grid.addWidget(self.chk_shuffle, 1, 3)
        
        left_layout.addWidget(settings_group)
        
        # Area 3: Model Selection & Train Commands
        model_group = QGroupBox("3. ML Algorithms Selection")
        model_v_layout = QVBoxLayout(model_group)
        model_v_layout.setSpacing(6)
        
        # Algorithm Checkboxes
        self.models_chk = {}
        models_list = [
            "Random Forest",
            "Support Vector Machine",
            "MLP Neural Network",
            "K-Nearest Neighbor",
            "Decision Tree",
            "Logistic Regression"
        ]
        
        chk_grid = QGridLayout()
        chk_grid.setSpacing(8)
        for idx, model_name in enumerate(models_list):
            chk = QCheckBox(model_name)
            chk.setChecked(True)
            self.models_chk[model_name] = chk
            chk_grid.addWidget(chk, idx // 2, idx % 2)
        model_v_layout.addLayout(chk_grid)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_train_sel = QPushButton("Train Selected")
        self.btn_train_sel.setObjectName("TrainSelectedBtn")
        self.btn_train_sel.clicked.connect(self.train_selected)
        btn_layout.addWidget(self.btn_train_sel)
        
        self.btn_train_all = QPushButton("Train All")
        self.btn_train_all.setObjectName("TrainAllBtn")
        self.btn_train_all.clicked.connect(self.train_all)
        btn_layout.addWidget(self.btn_train_all)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_training)
        btn_layout.addWidget(self.btn_stop)
        
        model_v_layout.addLayout(btn_layout)
        left_layout.addWidget(model_group)
        
        # Real-time Scrolling Console Log Panel
        log_group = QGroupBox("Execution Terminal Log")
        log_v_layout = QVBoxLayout(log_group)
        self.log_console = QTextEdit()
        self.log_console.setObjectName("LogConsole")
        self.log_console.setReadOnly(True)
        log_v_layout.addWidget(self.log_console)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        log_v_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(log_group)
        
        # Set left widget fixed width ratio or size
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_panel)
        left_scroll.setFrameShape(QFrame.NoFrame)
        splitter.addWidget(left_scroll)
        
        # Right Panel (Tab Widgets for charts, tables, comparisons)
        right_panel = QTabWidget()
        right_panel.setObjectName("RightTabWidget")
        
        # Tab 1: Dataset Distribution Chart
        self.tab_dataset_dist = QWidget()
        tab_dist_layout = QVBoxLayout(self.tab_dataset_dist)
        self.canvas_dist = MplCanvas(width=6, height=5, dpi=100)
        tab_dist_layout.addWidget(self.canvas_dist)
        right_panel.addTab(self.tab_dataset_dist, "Dataset Distribution")
        
        # Tab 2: Model Comparison Chart (Accuracy, F1, Time)
        self.tab_model_comp = QWidget()
        tab_comp_layout = QVBoxLayout(self.tab_model_comp)
        
        # We can alternate plotting Accuracy/F1 and training times or show them stacked.
        # Let's put a sub tab or layout containing both side by side or stacked.
        self.canvas_comp = MplCanvas(width=6, height=3, dpi=100)
        self.canvas_time = MplCanvas(width=6, height=3, dpi=100)
        
        tab_comp_layout.addWidget(self.canvas_comp)
        tab_comp_layout.addWidget(self.canvas_time)
        right_panel.addTab(self.tab_model_comp, "Model Comparison Charts")
        
        # Tab 3: Detailed Evaluation (Confusion Matrix, Feature Importances, Learning Curve)
        self.tab_detailed_eval = QWidget()
        tab_detail_layout = QHBoxLayout(self.tab_detailed_eval)
        
        # Selector for detailed view
        selector_widget = QGroupBox("Select Model for Analysis")
        selector_widget.setMaximumWidth(220)
        selector_v_layout = QVBoxLayout(selector_widget)
        
        self.detail_model_combo = QComboBox()
        self.detail_model_combo.currentIndexChanged.connect(self.update_detailed_plots)
        selector_v_layout.addWidget(self.detail_model_combo)
        selector_v_layout.addStretch()
        tab_detail_layout.addWidget(selector_widget)
        
        # Embedded figures for detailed view (Confusion Matrix and Feature Importance / Learning curve)
        plots_widget = QWidget()
        plots_grid = QGridLayout(plots_widget)
        self.canvas_cm = MplCanvas(width=4, height=4, dpi=100)
        self.canvas_feat_imp = MplCanvas(width=4, height=4, dpi=100)
        plots_grid.addWidget(self.canvas_cm, 0, 0)
        plots_grid.addWidget(self.canvas_feat_imp, 0, 1)
        tab_detail_layout.addWidget(plots_widget)
        
        right_panel.addTab(self.tab_detailed_eval, "Detailed Evaluation Charts")
        
        # Tab 4: Performance Table
        self.tab_table = QWidget()
        tab_table_layout = QVBoxLayout(self.tab_table)
        
        self.comparison_table = QTableWidget(0, 8)
        self.comparison_table.setHorizontalHeaderLabels([
            "Model Name", "Accuracy", "Precision", "Recall", 
            "F1-Score", "Train Time (s)", "Pred Time (s)", "Memory Footprint"
        ])
        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_table_layout.addWidget(self.comparison_table)
        right_panel.addTab(self.tab_table, "Comparison Table")
        
        # Tab 5: Exports & Deployment
        self.tab_exports = QWidget()
        tab_exp_layout = QVBoxLayout(self.tab_exports)
        
        # Display Box for Best Model
        best_box = QGroupBox("Selected Champion Model Details")
        best_grid = QGridLayout(best_box)
        
        best_grid.addWidget(QLabel("Algorithm Name:"), 0, 0)
        self.best_name_val = QLabel("None")
        self.best_name_val.setStyleSheet("font-weight: bold; font-size: 16px; color: #00E5FF;")
        best_grid.addWidget(self.best_name_val, 0, 1)
        
        best_grid.addWidget(QLabel("Accuracy:"), 0, 2)
        self.best_acc_val = QLabel("0.0%")
        self.best_acc_val.setStyleSheet("font-weight: bold; font-size: 16px; color: #00E5FF;")
        best_grid.addWidget(self.best_acc_val, 0, 3)

        best_grid.addWidget(QLabel("Scaler State:"), 1, 0)
        self.best_scaler_val = QLabel("None")
        self.best_scaler_val.setStyleSheet("color: #FFFFFF;")
        best_grid.addWidget(self.best_scaler_val, 1, 1)
        
        best_grid.addWidget(QLabel("Saved File Location:"), 1, 2)
        self.best_file_val = QLabel("models/gesture_model.pkl")
        self.best_file_val.setStyleSheet("color: #8A2BE2;")
        best_grid.addWidget(self.best_file_val, 1, 3)
        
        tab_exp_layout.addWidget(best_box)
        
        # Exports Group
        exports_box = QGroupBox("Export Project Artifacts")
        exports_v = QVBoxLayout(exports_box)
        
        pdf_h = QHBoxLayout()
        pdf_h.addWidget(QLabel("Compile training report as PDF (contains graphs, details):"))
        self.btn_export_pdf = QPushButton("Export PDF Report")
        self.btn_export_pdf.clicked.connect(self.export_pdf_report)
        self.btn_export_pdf.setEnabled(False)
        pdf_h.addWidget(self.btn_export_pdf)
        exports_v.addLayout(pdf_h)
        
        csv_h = QHBoxLayout()
        csv_h.addWidget(QLabel("Export full models performance results in CSV format:"))
        self.btn_export_csv = QPushButton("Export CSV Metrics")
        self.btn_export_csv.clicked.connect(self.export_csv_results)
        self.btn_export_csv.setEnabled(False)
        csv_h.addWidget(self.btn_export_csv)
        exports_v.addLayout(csv_h)
        
        logs_h = QHBoxLayout()
        logs_h.addWidget(QLabel("Export compilation logs from this session to a log text file:"))
        self.btn_export_log = QPushButton("Export Session Logs")
        self.btn_export_log.clicked.connect(self.export_session_logs)
        self.btn_export_log.setEnabled(False)
        logs_h.addWidget(self.btn_export_log)
        exports_v.addLayout(logs_h)
        
        tab_exp_layout.addWidget(exports_box)
        tab_exp_layout.addStretch()
        
        right_panel.addTab(self.tab_exports, "Export & Deployment")
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (e.g. 40% left, 60% right)
        splitter.setSizes([450, 850])

    def log(self, text):
        """
        Appends a line of text to the UI scrolling text console log.
        """
        timestamp = time.strftime("[%H:%M:%S]")
        formatted_log = f"{timestamp} {text}"
        self.log_console.append(formatted_log)
        self.log_accumulator += formatted_log + "\n"
        
        # Auto-scroll to the bottom
        self.log_console.moveCursor(QTextCursor.End)

    def browse_dataset(self):
        """
        Opens a file picker dialog to let the user select a dataset CSV file.
        """
        file_filter = "CSV Files (*.csv)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Gesture Dataset CSV", "dataset", file_filter)
        
        if file_path:
            # Standardize path separators for Windows
            file_path = os.path.abspath(file_path)
            
            # Update combobox path
            if self.dataset_path_le.findText(file_path) == -1:
                self.dataset_path_le.addItem(file_path)
            self.dataset_path_le.setCurrentText(file_path)
            
            self.log(f"Selected file: {file_path}")
            self.load_dataset(file_path)

    def load_dataset(self, file_path):
        """
        Uses DatasetLoader to parse the CSV file and update metrics and graphs.
        """
        self.log("Loading dataset and analyzing distribution...")
        loader = DatasetLoader(file_path)
        success, msg, stats = loader.load_and_analyze()
        
        if not success:
            self.log(f"Error loading dataset: {msg}")
            QMessageBox.critical(self, "Load Error", f"Failed to load dataset:\n{msg}")
            return
            
        self.dataset_stats = stats
        self.X, self.y = loader.get_data()
        self.dataset_loaded = True
        
        # Update statistics labels in GUI
        self.lbl_samples.setText(str(stats["samples_count"]))
        self.lbl_features.setText(str(stats["features_count"]))
        self.lbl_classes.setText(str(stats["classes_count"]))
        self.lbl_nan.setText(str(stats["nan_count"]))
        
        # Update class distribution table
        self.dist_table.setRowCount(0)
        dist = stats["class_distribution"]
        for row_idx, (gesture, count) in enumerate(dist.items()):
            self.dist_table.insertRow(row_idx)
            self.dist_table.setItem(row_idx, 0, QTableWidgetItem(gesture))
            self.dist_table.setItem(row_idx, 1, QTableWidgetItem(str(count)))
            
        self.log(f"Dataset successfully loaded. Samples: {stats['samples_count']}, Classes: {stats['classes_count']}.")
        
        # Check balance
        preprocessor = Preprocessor()
        is_balanced, ratio, balance_summary = preprocessor.check_balance(self.y)
        self.log(f"Dataset balance check: {balance_summary}")
        if not is_balanced:
            self.log("Warning: The dataset is significantly imbalanced. Consider collecting more samples for minority gestures.")

        # Plot distribution chart in Tab 1
        self.plot_distribution_chart()

    def plot_distribution_chart(self):
        """
        Plots a bar chart of class distribution.
        """
        if not self.dataset_loaded:
            return
            
        dist = self.dataset_stats["class_distribution"]
        classes = list(dist.keys())
        counts = list(dist.values())
        
        fig = self.canvas_dist.figure
        fig.clear()
        ax = fig.add_subplot(111)
        
        # Dark styling
        ax.set_facecolor('#262626')
        ax.tick_params(colors='#E0E0E0')
        ax.xaxis.label.set_color('#E0E0E0')
        ax.yaxis.label.set_color('#E0E0E0')
        ax.title.set_color('#E0E0E0')
        for spine in ax.spines.values():
            spine.set_color('#444444')
            
        # Draw horizontal bars
        y_pos = range(len(classes))
        bars = ax.barh(y_pos, counts, align='center', color='#8A2BE2')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(classes, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel('Samples Count', fontsize=10)
        ax.set_title('Gesture Class Dataset Distribution', fontsize=12, fontweight='bold', pad=15)
        
        # Add labels to bars
        for bar in bars:
            width = bar.get_width()
            ax.annotate(f' {width}',
                        xy=(width, bar.get_y() + bar.get_height() / 2),
                        xytext=(0, 0), textcoords="offset points",
                        ha='left', va='center', fontsize=9, color='#E0E0E0')
                        
        fig.tight_layout()
        self.canvas_dist.draw()

    def get_selected_models(self):
        """
        Returns a list of model names that have been checked by the user.
        """
        return [name for name, chk in self.models_chk.items() if chk.isChecked()]

    def train_selected(self):
        """
        Launches training for checked models.
        """
        self.run_training_pipeline(self.get_selected_models())

    def train_all(self):
        """
        Launches training for all supported models.
        """
        # Set all checkboxes to checked
        for chk in self.models_chk.values():
            chk.setChecked(True)
        self.run_training_pipeline(list(self.models_chk.keys()))

    def stop_training(self):
        """
        Halts the executing worker thread.
        """
        if self.training_thread and self.training_thread.isRunning():
            self.log("Sending cancellation request to training thread...")
            self.training_thread.stop()
            self.btn_stop.setEnabled(False)

    def run_training_pipeline(self, selected_models):
        """
        Sets up the preprocessor, splits the dataset, and runs the QThread training runner.
        """
        if not self.dataset_loaded:
            QMessageBox.warning(self, "No Dataset", "Please load a dataset CSV first.")
            return
            
        if not selected_models:
            QMessageBox.warning(self, "No Models Selected", "Please select at least one algorithm to train.")
            return

        # Prepare UI for training
        self.set_ui_interactive(False)
        self.progress_bar.setValue(0)
        self.log_accumulator = "" # reset export log
        self.log("Initializing preprocessor for training data...")

        # Parse settings
        ratio_str = self.ratio_combo.currentText()
        test_ratio = 0.2
        if ratio_str == "70/30": test_ratio = 0.3
        elif ratio_str == "75/25": test_ratio = 0.25
        elif ratio_str == "90/10": test_ratio = 0.1
        
        cv_folds_str = self.cv_combo.currentText()
        cv_folds = 5
        if "10" in cv_folds_str: cv_folds = 10
        elif "3" in cv_folds_str: cv_folds = 3
        elif "2" in cv_folds_str: cv_folds = 2

        seed = self.seed_spin.value()
        normalize = self.chk_normalize.isChecked()
        shuffle = self.chk_shuffle.isChecked()

        settings = {
            "ratio": ratio_str,
            "test_ratio": test_ratio,
            "cv_folds": cv_folds,
            "seed": seed,
            "normalize": normalize,
            "shuffle": shuffle
        }

        # Step 1: Preprocess and Split Data
        preprocessor = Preprocessor()
        self.log(f"Splitting dataset using Stratified Split ({100 - int(test_ratio*100)}/{int(test_ratio*100)}) with seed {seed}...")
        
        try:
            X_train, X_test, y_train, y_test = preprocessor.split_dataset(
                self.X, self.y,
                test_size=test_ratio,
                shuffle=shuffle,
                random_state=seed
            )
            self.log(f"Splitting complete. Train shape: {X_train.shape}, Test shape: {X_test.shape}")
        except Exception as e:
            self.log(f"Error during splitting: {str(e)}")
            self.set_ui_interactive(True)
            return

        # Step 2: Initialize Worker QThread
        self.training_thread = ModelTrainingWorker(X_train, X_test, y_train, y_test, selected_models, settings)
        
        # Connect signals
        self.training_thread.log_signal.connect(self.log)
        self.training_thread.progress_signal.connect(self.progress_bar.setValue)
        self.training_thread.model_trained_signal.connect(self.handle_model_trained)
        self.training_thread.finished_signal.connect(self.handle_training_finished)
        self.training_thread.error_signal.connect(self.handle_training_error)
        
        # Start execution
        self.btn_stop.setEnabled(True)
        self.training_thread.start()

    def set_ui_interactive(self, enabled):
        """
        Disables UI controls during active QThread background runs.
        """
        self.browse_btn.setEnabled(enabled)
        self.btn_train_sel.setEnabled(enabled)
        self.btn_train_all.setEnabled(enabled)
        self.ratio_combo.setEnabled(enabled)
        self.seed_spin.setEnabled(enabled)
        self.cv_combo.setEnabled(enabled)
        self.chk_normalize.setEnabled(enabled)
        self.chk_shuffle.setEnabled(enabled)
        
        for chk in self.models_chk.values():
            chk.setEnabled(enabled)

    @Slot(str, dict)
    def handle_model_trained(self, model_name, results):
        """
        Stores results of trained models incrementally.
        """
        self.trained_results[model_name] = results
        self.log(f"Successfully recorded training metrics for: {model_name}")

    @Slot(dict, str)
    def handle_training_finished(self, all_results, best_model_name):
        """
        Triggered when QThread finishes training execution. Updates charts, exports configuration, and best model values.
        """
        self.trained_results = all_results
        self.best_model_name = best_model_name
        
        self.set_ui_interactive(True)
        self.btn_stop.setEnabled(False)
        
        if not all_results:
            self.log("Training complete, but no models were built.")
            return

        # Update detailed comparison model dropdown
        self.detail_model_combo.blockSignals(True)
        self.detail_model_combo.clear()
        self.detail_model_combo.addItems(list(all_results.keys()))
        self.detail_model_combo.blockSignals(False)

        # Update Comparison Table
        self.update_comparison_table()

        # Update Best Model Display Badge
        best_acc = all_results[best_model_name]["accuracy"] * 100
        self.best_model_lbl.setText(f"{best_model_name} ({best_acc:.2f}% Acc)")
        self.best_model_lbl.setStyleSheet("color: #00FFCC; font-weight: bold; font-size: 14px;")

        # Update Exports Tab View
        self.best_name_val.setText(best_model_name)
        self.best_acc_val.setText(f"{best_acc:.4f}%")
        
        has_scaler = all_results[best_model_name]["scaler_object"] is not None
        self.best_scaler_val.setText("StandardScaler Saved" if has_scaler else "None Required")
        
        # Save model and scaler files to models/ dir automatically
        self.log("Saving champion model to disk...")
        success, save_msg = ModelManager.save_best_model("models", best_model_name, all_results)
        self.log(save_msg)

        # Plot charts
        self.plot_comparison_charts()
        
        # Trigger detail charts plot for first model
        self.update_detailed_plots()

        # Enable Export Buttons
        self.btn_export_pdf.setEnabled(True)
        self.btn_export_csv.setEnabled(True)
        self.btn_export_log.setEnabled(True)

        QMessageBox.information(self, "Pipeline Complete", f"All selected algorithms trained successfully!\nBest model: {best_model_name} saved to disk.")

    @Slot(str)
    def handle_training_error(self, err_msg):
        self.log(f"CRITICAL ERROR during training: {err_msg}")
        QMessageBox.critical(self, "Training Error", f"A critical error occurred:\n{err_msg}")
        self.set_ui_interactive(True)
        self.btn_stop.setEnabled(False)

    def update_comparison_table(self):
        """
        Populates the grid comparison table with metrics from trained models.
        """
        self.comparison_table.setRowCount(0)
        comparator = ModelComparison(self.trained_results)
        df = comparator.get_comparison_table()
        
        for i, row in df.iterrows():
            self.comparison_table.insertRow(i)
            for j in range(df.shape[1]):
                val = str(row.iloc[j])
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                # Highlight best model row with cyan font
                if row["Model"] == self.best_model_name:
                    item.setForeground(QColor("#00E5FF"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.comparison_table.setItem(i, j, item)

    def plot_comparison_charts(self):
        """
        Plots metric comparisons using Matplotlib.
        """
        ModelComparison.plot_metric_comparison(self.canvas_comp.figure, self.trained_results)
        self.canvas_comp.draw()
        
        ModelComparison.plot_time_comparison(self.canvas_time.figure, self.trained_results)
        self.canvas_time.draw()

    def update_detailed_plots(self):
        """
        Plots confusion matrix and feature importance for the selected model.
        """
        model_name = self.detail_model_combo.currentText()
        if not model_name:
            return
            
        res = self.trained_results.get(model_name)
        if not res:
            return
            
        classes = self.dataset_stats.get("class_list", [])
        
        # 1. Confusion Matrix
        fig_cm = self.canvas_cm.figure
        fig_cm.clear()
        ax = fig_cm.add_subplot(111)
        
        # Draw CM
        cm = res["confusion_matrix"]
        
        fig_cm.patch.set_facecolor('#1A1A1A')
        ax.set_facecolor('#262626')
        
        im = ax.imshow(cm, interpolation='nearest', cmap=matplotlib.colormaps['Blues'])
        ax.title.set_color('#E0E0E0')
        ax.tick_params(colors='#E0E0E0')
        ax.set_title(f'Confusion Matrix: {model_name}', fontsize=11, fontweight='bold', pad=12)
        
        # Tick Labels
        tick_marks = range(len(classes))
        ax.set_xticks(tick_marks)
        ax.set_xticklabels(classes, rotation=45, ha='right', fontsize=8)
        ax.set_yticks(tick_marks)
        ax.set_yticklabels(classes, fontsize=8)
        
        # Color scale bar
        cbar = fig_cm.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(colors='#E0E0E0')
        
        # Fill cells with numbers
        thresh = cm.max() / 2.0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, format(cm[i, j], 'd'),
                        ha="center", va="center",
                        color="white" if cm[i, j] > thresh else "black",
                        fontsize=8)
                        
        ax.set_ylabel('True Label', fontsize=9, color='#E0E0E0')
        ax.set_xlabel('Predicted Label', fontsize=9, color='#E0E0E0')
        fig_cm.tight_layout()
        self.canvas_cm.draw()
        
        # 2. Feature Importance
        ModelComparison.plot_feature_importance(self.canvas_feat_imp.figure, self.trained_results, model_name)
        self.canvas_feat_imp.draw()

    def export_pdf_report(self):
        """
        Creates and saves a PDF training report.
        """
        file_filter = "PDF Files (*.pdf)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Training Report PDF", "Training_Report.pdf", file_filter)
        
        if file_path:
            self.log(f"Compiling PDF Report at: {file_path}...")
            
            # Setup settings dict
            ratio_str = self.ratio_combo.currentText()
            cv_folds = 5
            if "10" in self.cv_combo.currentText(): cv_folds = 10
            elif "3" in self.cv_combo.currentText(): cv_folds = 3
            elif "2" in self.cv_combo.currentText(): cv_folds = 2
            
            settings = {
                "ratio": ratio_str,
                "seed": self.seed_spin.value(),
                "cv_folds": cv_folds,
                "normalize": self.chk_normalize.isChecked(),
                "shuffle": self.chk_shuffle.isChecked()
            }
            
            generator = ReportGenerator(self.trained_results, self.best_model_name, self.dataset_stats, settings)
            success, msg = generator.generate_pdf_report(file_path)
            self.log(msg)
            
            if success:
                QMessageBox.information(self, "Export Successful", "PDF Training Report generated successfully!")
            else:
                QMessageBox.critical(self, "Export Error", f"Failed to export PDF:\n{msg}")

    def export_csv_results(self):
        """
        Exports metrics results comparison spreadsheet.
        """
        file_filter = "CSV Files (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Performance Metrics CSV", "model_comparison.csv", file_filter)
        
        if file_path:
            generator = ReportGenerator(self.trained_results, self.best_model_name, self.dataset_stats, {})
            success, msg = generator.export_csv_results(file_path)
            self.log(msg)
            
            if success:
                QMessageBox.information(self, "Export Successful", "CSV Results file exported successfully!")
            else:
                QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{msg}")

    def export_session_logs(self):
        """
        Exports the contents of the logging console.
        """
        file_filter = "Log Files (*.log *.txt)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Compilation Logs", "training_session.log", file_filter)
        
        if file_path:
            generator = ReportGenerator(self.trained_results, self.best_model_name, self.dataset_stats, {})
            success, msg = generator.export_log(file_path, self.log_accumulator)
            self.log(msg)
            
            if success:
                QMessageBox.information(self, "Export Successful", "Session logs saved successfully!")
            else:
                QMessageBox.critical(self, "Export Error", f"Failed to export logs:\n{msg}")
