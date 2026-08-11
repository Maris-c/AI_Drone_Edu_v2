import sys
import os
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, 
    QFileDialog, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QSplitter, QProgressBar, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor

from .evaluator_engine import EvaluatorEngine
from .pdf_exporter import PDFExporter

DARK_THEME_STYLE = """
QMainWindow {
    background-color: #0F172A;
}
QWidget {
    color: #F8FAFC;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    background-color: #0F172A;
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
QPushButton#btn_export {
    background-color: #10B981;
}
QPushButton#btn_export:hover {
    background-color: #059669;
}
QPushButton#btn_danger {
    background-color: #EF4444;
}
QPushButton#btn_danger:hover {
    background-color: #DC2626;
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
"""

class EvaluationWorker(QThread):
    progress_signal = Signal(int, str)
    finished_signal = Signal(list)

    def __init__(self, models_to_evaluate, engine):
        super().__init__()
        self.models = models_to_evaluate
        self.engine = engine

    def run(self):
        results_list = []
        total = len(self.models)
        for i, model_path in enumerate(self.models):
            self.progress_signal.emit(int((i / total) * 100), f"Evaluating {os.path.basename(model_path)}...")
            res = self.engine.evaluate(model_path)
            results_list.append(res)
            
        self.progress_signal.emit(100, "Evaluation Complete!")
        self.finished_signal.emit(results_list)

class ModelComparisonUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(DARK_THEME_STYLE)
        
        self.engine = EvaluatorEngine()
        self.model_paths = []
        self.results_data = []
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Header
        lbl_title = QLabel("AI DRONE - MULTI-MODEL COMPARISON & BENCHMARKING")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: #38BDF8; margin-bottom: 10px;")
        main_layout.addWidget(lbl_title)

        splitter = QSplitter(Qt.Vertical)
        
        # Top Panel: Model List
        group_models = QGroupBox("Selected Models for Comparison")
        g_model_layout = QVBoxLayout(group_models)
        
        self.table_models = QTableWidget(0, 7)
        self.table_models.setHorizontalHeaderLabels(["Model Path", "Size (KB)", "Latency (ms)", "FPS", "Throughput", "RAM (MB)", "Status"])
        self.table_models.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 7):
            self.table_models.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        g_model_layout.addWidget(self.table_models)
        
        h_model_btns = QHBoxLayout()
        btn_add = QPushButton("Add Model(s)")
        btn_add.clicked.connect(self.add_models)
        
        btn_remove = QPushButton("Remove Selected")
        btn_remove.setObjectName("btn_danger")
        btn_remove.clicked.connect(self.remove_model)
        
        self.btn_run = QPushButton("Run Comparison Benchmark")
        self.btn_run.clicked.connect(self.run_benchmark)
        
        self.btn_export = QPushButton("Export PDF Report")
        self.btn_export.setObjectName("btn_export")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_pdf)
        
        h_model_btns.addWidget(btn_add)
        h_model_btns.addWidget(btn_remove)
        h_model_btns.addStretch()
        h_model_btns.addWidget(self.btn_run)
        h_model_btns.addWidget(self.btn_export)
        
        g_model_layout.addLayout(h_model_btns)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("Ready.")
        g_model_layout.addWidget(self.progress_bar)
        g_model_layout.addWidget(self.lbl_status)
        
        splitter.addWidget(group_models)
        
        # Bottom Panel: Visual Comparison
        group_charts = QGroupBox("Performance Charts")
        g_charts_layout = QVBoxLayout(group_charts)
        
        # Setup Matplotlib canvases
        self.tabs_charts = QTabWidget()
        
        # Latency & FPS Chart
        self.fig_perf = Figure(figsize=(8, 4), facecolor='#1E293B')
        self.canvas_perf = FigureCanvas(self.fig_perf)
        self.tabs_charts.addTab(self.canvas_perf, "Latency & FPS")
        
        # Size & RAM Chart
        self.fig_res = Figure(figsize=(8, 4), facecolor='#1E293B')
        self.canvas_res = FigureCanvas(self.fig_res)
        self.tabs_charts.addTab(self.canvas_res, "Size & Memory")
        
        g_charts_layout.addWidget(self.tabs_charts)
        splitter.addWidget(group_charts)
        
        main_layout.addWidget(splitter)

    def add_models(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Models", "", 
            "Model Files (*.pkl *.joblib *.onnx *.pt *.pth *.tflite)"
        )
        for path in paths:
            if path not in self.model_paths:
                self.model_paths.append(path)
                
        self.refresh_table()

    def remove_model(self):
        selected = self.table_models.selectedItems()
        if not selected:
            return
            
        rows_to_remove = set([item.row() for item in selected])
        
        # Remove in reverse order to not mess up indices
        for row in sorted(list(rows_to_remove), reverse=True):
            del self.model_paths[row]
            
        self.refresh_table()

    def refresh_table(self):
        self.table_models.setRowCount(0)
        for path in self.model_paths:
            row = self.table_models.rowCount()
            self.table_models.insertRow(row)
            self.table_models.setItem(row, 0, QTableWidgetItem(path))
            for col in range(1, 7):
                self.table_models.setItem(row, col, QTableWidgetItem("-"))
            self.table_models.setItem(row, 6, QTableWidgetItem("Pending"))

    def run_benchmark(self):
        if not self.model_paths:
            QMessageBox.warning(self, "No Models", "Please add at least one model to evaluate.")
            return
            
        self.btn_run.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.results_data = []
        
        self.worker = EvaluationWorker(self.model_paths, self.engine)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_benchmark_finished)
        self.worker.start()

    def update_progress(self, val, text):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(text)

    def on_benchmark_finished(self, results):
        self.results_data = results
        self.btn_run.setEnabled(True)
        self.btn_export.setEnabled(True)
        
        # Update Table
        for row, res in enumerate(self.results_data):
            if res.get("error"):
                self.table_models.setItem(row, 6, QTableWidgetItem(f"Error: {res['error']}"))
                self.table_models.item(row, 6).setForeground(QColor("#EF4444"))
                continue
                
            self.table_models.setItem(row, 1, QTableWidgetItem(f"{res['model_size_kb']:.2f}"))
            self.table_models.setItem(row, 2, QTableWidgetItem(f"{res['latency_ms']:.3f}"))
            self.table_models.setItem(row, 3, QTableWidgetItem(f"{res['fps']:.1f}"))
            self.table_models.setItem(row, 4, QTableWidgetItem(f"{res['throughput']:.1f}"))
            self.table_models.setItem(row, 5, QTableWidgetItem(f"{res['ram_usage_mb']:.1f}"))
            self.table_models.setItem(row, 6, QTableWidgetItem("Success"))
            self.table_models.item(row, 6).setForeground(QColor("#10B981"))
            
        self.update_charts()

    def update_charts(self):
        valid_res = [r for r in self.results_data if not r.get("error")]
        if not valid_res:
            return
            
        labels = [r["model_name"][:15] + "..." if len(r["model_name"]) > 15 else r["model_name"] for r in valid_res]
        
        # 1. Latency & FPS Chart
        self.fig_perf.clear()
        ax1 = self.fig_perf.add_subplot(121)
        ax1.set_facecolor('#1E293B')
        latencies = [r["latency_ms"] for r in valid_res]
        bars1 = ax1.bar(labels, latencies, color='#EF4444')
        ax1.set_title("Latency (ms) [Lower=Better]", color='white', fontsize=10)
        ax1.tick_params(axis='x', rotation=45, colors='white', labelsize=8)
        ax1.tick_params(axis='y', colors='white')
        self._add_bar_labels(ax1, bars1)
        
        ax2 = self.fig_perf.add_subplot(122)
        ax2.set_facecolor('#1E293B')
        fps = [r["fps"] for r in valid_res]
        bars2 = ax2.bar(labels, fps, color='#10B981')
        ax2.set_title("FPS [Higher=Better]", color='white', fontsize=10)
        ax2.tick_params(axis='x', rotation=45, colors='white', labelsize=8)
        ax2.tick_params(axis='y', colors='white')
        self._add_bar_labels(ax2, bars2)
        
        self.fig_perf.tight_layout()
        self.canvas_perf.draw()

        # 2. Size & RAM Chart
        self.fig_res.clear()
        ax3 = self.fig_res.add_subplot(121)
        ax3.set_facecolor('#1E293B')
        sizes = [r["model_size_kb"] for r in valid_res]
        bars3 = ax3.bar(labels, sizes, color='#F59E0B')
        ax3.set_title("Model Size (KB) [Lower=Better]", color='white', fontsize=10)
        ax3.tick_params(axis='x', rotation=45, colors='white', labelsize=8)
        ax3.tick_params(axis='y', colors='white')
        self._add_bar_labels(ax3, bars3)

        ax4 = self.fig_res.add_subplot(122)
        ax4.set_facecolor('#1E293B')
        rams = [r["ram_usage_mb"] for r in valid_res]
        bars4 = ax4.bar(labels, rams, color='#3B82F6')
        ax4.set_title("RAM Overhead (MB) [Lower=Better]", color='white', fontsize=10)
        ax4.tick_params(axis='x', rotation=45, colors='white', labelsize=8)
        ax4.tick_params(axis='y', colors='white')
        self._add_bar_labels(ax4, bars4)

        self.fig_res.tight_layout()
        self.canvas_res.draw()

    def _add_bar_labels(self, ax, bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  
                        textcoords="offset points",
                        ha='center', va='bottom', color='white', fontsize=8, fontweight='bold')

    def export_pdf(self):
        valid_res = [r for r in self.results_data if not r.get("error")]
        if not valid_res:
            QMessageBox.warning(self, "No Data", "No successful evaluations to export.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "model_comparison_report.pdf", "PDF Files (*.pdf)")
        if save_path:
            exporter = PDFExporter(valid_res)
            success, msg = exporter.generate_pdf(save_path)
            if success:
                QMessageBox.information(self, "Success", f"Report saved successfully to:\n{save_path}")
            else:
                QMessageBox.critical(self, "Error", f"Failed to save PDF:\n{msg}")
