from PySide6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from app.pages.base_page import BasePage
from app.widgets.card import Card
from PySide6.QtCore import Qt

class SimulatorPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("3D Simulator", parent)

        # Main horizontal split
        hbox = QHBoxLayout()
        hbox.setSpacing(16)

        # Left: Large simulated canvas representing the 3D view
        sim_view = Card(self)
        sim_view.setStyleSheet("background-color: #08090d; border: 2px dashed #222536;")
        
        sim_lbl = QLabel("3D Drone Simulator Viewport")
        sim_lbl.setObjectName("h2")
        sim_lbl.setAlignment(Qt.AlignCenter)
        
        sim_sub = QLabel("Open3D / PyOpenGL Rendering Canvas Placeholder")
        sim_sub.setObjectName("secondary")
        sim_sub.setAlignment(Qt.AlignCenter)
        
        sim_view.layout.addStretch(1)
        sim_view.layout.addWidget(sim_lbl)
        sim_view.layout.addWidget(sim_sub)
        sim_view.layout.addStretch(1)
        
        hbox.addWidget(sim_view, 7)

        # Right: Physics & Environment Configuration Controls
        controls = Card(self)
        controls.setFixedWidth(260)
        
        ctrl_title = QLabel("Simulation Controls")
        ctrl_title.setObjectName("h2")
        controls.layout.addWidget(ctrl_title)

        # Mock buttons
        self.btn_spawn = QPushButton("Spawn Virtual Drone")
        self.btn_wind = QPushButton("Enable Wind Turbulence")
        self.btn_reset = QPushButton("Reset Physics state")
        
        self.btn_spawn.setStyleSheet("background-color: #7C4DFF; color: #FFFFFF;")
        
        controls.layout.addWidget(self.btn_spawn)
        controls.layout.addWidget(self.btn_wind)
        controls.layout.addWidget(self.btn_reset)
        controls.layout.addStretch()

        hbox.addWidget(controls, 3)
        self.main_layout.addLayout(hbox)
