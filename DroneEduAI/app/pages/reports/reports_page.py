from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout
from app.pages.base_page import BasePage
from app.widgets.card import Card
from PySide6.QtCore import Qt

class ReportsPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("Mission Reports", parent)

        # Overview Card
        intro = Card(self)
        intro_title = QLabel("Recorded Mission Analytics Logs")
        intro_title.setObjectName("h2")
        intro_desc = QLabel("Review past flight records, telemetry status signals, and hand gesture model performance logs.")
        intro_desc.setObjectName("secondary")
        intro.layout.addWidget(intro_title)
        intro.layout.addWidget(intro_desc)
        self.main_layout.addWidget(intro)

        # Log Table Card
        table_card = Card(self)
        self.table = QTableWidget(4, 5, self)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Mission Name", "Total Blocks", "AI Accuracy", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                gridline-color: #222536;
                border: none;
            }
            QHeaderView::section {
                background-color: #10111A;
                color: #8E94B2;
                padding: 6px;
                border: 1px solid #222536;
                font-weight: bold;
            }
        """)

        # Fill dummy logs
        logs = [
            ("2026-08-06 17:15", "Auto-Takeoff Loop", "8", "99.1%", "Export PDF"),
            ("2026-08-06 15:40", "Visual Land Test", "4", "97.5%", "Export PDF"),
            ("2026-08-05 11:22", "Forward Hover Mission", "12", "98.9%", "Export PDF"),
            ("2026-08-04 09:05", "Manual Hand Gesture Run", "6", "94.2%", "Export PDF"),
        ]

        for row_idx, data in enumerate(logs):
            for col_idx, text in enumerate(data[:-1]):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setForeground(Qt.white)
                self.table.setItem(row_idx, col_idx, item)
            
            # Action button inside cell
            btn = QPushButton("Export PDF")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #7C4DFF;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #9b72ff;
                }
            """)
            self.table.setCellWidget(row_idx, 4, btn)

        table_card.layout.addWidget(self.table)
        self.main_layout.addWidget(table_card)
        self.main_layout.addStretch()
