from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QProgressBar
from app.pages.base_page import BasePage
from app.widgets.card import Card
from PySide6.QtCore import Qt

class StatCard(Card):
    def __init__(self, title, val, subtitle, accent_color="#7C4DFF", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(130)
        
        lbl_title = QLabel(title.upper())
        lbl_title.setObjectName("secondary")
        lbl_title.setStyleSheet("letter-spacing: 1px; font-weight: bold;")
        
        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {accent_color};")
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setObjectName("secondary")
        
        self.layout.addWidget(lbl_title)
        self.layout.addWidget(lbl_val)
        self.layout.addWidget(lbl_sub)


class DashboardPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("Dashboard", parent)
        
        # Grid of stats cards
        grid = QGridLayout()
        grid.setSpacing(16)
        
        self.card_uav = StatCard("Active UAV", "DISCONNECTED", "Configure MAVLink ports in Settings", "#FF1744", self)
        self.card_ai = StatCard("AI Model", "MediaPipe RF", "98.4% validation accuracy", "#7C4DFF", self)
        self.card_dataset = StatCard("Recorded Dataset", "1,240 Samples", "9 distinct hand gestures", "#00E5FF", self)
        self.card_mission = StatCard("Visual Code Blocks", "14 Blocks Loaded", "Auto-saves to workspace", "#00E676", self)
        
        grid.addWidget(self.card_uav, 0, 0)
        grid.addWidget(self.card_ai, 0, 1)
        grid.addWidget(self.card_dataset, 1, 0)
        grid.addWidget(self.card_mission, 1, 1)
        
        self.main_layout.addLayout(grid)
        
        # Platform Quick Start
        quick_start = Card(self)
        lbl_qs_title = QLabel("Platform Welcome & Quick Start")
        lbl_qs_title.setObjectName("h2")
        quick_start.layout.addWidget(lbl_qs_title)
        
        steps = [
            "1. Connect your web camera inside the <b>Code (Mission Builder)</b> workspace.",
            "2. Ensure the lighting checks display green indicators.",
            "3. Perform any gesture (e.g., Takeoff) inside the central box, holding it for 5 seconds.",
            "4. A visual block will appear on the workspace canvas automatically.",
            "5. Press the green <b>Run Mission</b> floating button to test your drone interaction sequence."
        ]
        for step in steps:
            lbl_step = QLabel(step)
            lbl_step.setStyleSheet("color: #8E94B2; font-size: 13px; line-height: 20px;")
            quick_start.layout.addWidget(lbl_step)
            
        self.main_layout.addWidget(quick_start)
        self.main_layout.addStretch()
