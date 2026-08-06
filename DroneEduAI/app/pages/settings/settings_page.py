from PySide6.QtWidgets import QLabel, QPushButton, QComboBox, QLineEdit, QFormLayout, QHBoxLayout, QSlider
from app.pages.base_page import BasePage
from app.widgets.card import Card
from PySide6.QtCore import Qt, Signal

class SettingsPage(BasePage):
    settings_applied = Signal(int, str, float)

    def __init__(self, parent=None):
        super().__init__("Settings", parent)

        # 1. Hardware Connection Settings
        hw_card = Card(self)
        hw_title = QLabel("Hardware & Connection Channels")
        hw_title.setObjectName("h2")
        hw_card.layout.addWidget(hw_title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setVerticalSpacing(16)
        
        self.cam_dropdown = QComboBox(self)
        self.cam_dropdown.addItems(["Default Webcam (0)", "Secondary Camera (1)", "Third Camera (2)"])
        self.cam_dropdown.setStyleSheet("background-color: #10111A; border: 1px solid #222536; padding: 6px; border-radius: 4px;")

        self.mav_port = QLineEdit("udp:127.0.0.1:14550", self)
        self.mav_port.setStyleSheet("background-color: #10111A; border: 1px solid #222536; padding: 6px; border-radius: 4px; color: white;")

        form.addRow(QLabel("Camera Device:"), self.cam_dropdown)
        form.addRow(QLabel("MAVLink Port:"), self.mav_port)
        hw_card.layout.addLayout(form)
        self.main_layout.addWidget(hw_card)

        # 2. AI & Detection Thresholds
        ai_card = Card(self)
        ai_title = QLabel("AI Landmark & Detection Settings")
        ai_title.setObjectName("h2")
        ai_card.layout.addWidget(ai_title)

        ai_form = QFormLayout()
        ai_form.setSpacing(12)
        
        # Detection Confidence Slider
        self.conf_slider = QSlider(Qt.Horizontal, self)
        self.conf_slider.setRange(50, 100)
        self.conf_slider.setValue(70)
        self.conf_slider.setStyleSheet("height: 20px;")
        
        # Stability timer duration
        self.timer_dur = QLineEdit("5.0", self)
        self.timer_dur.setStyleSheet("background-color: #10111A; border: 1px solid #222536; padding: 6px; border-radius: 4px; color: white;")
        
        ai_form.addRow(QLabel("Min confidence threshold (%):"), self.conf_slider)
        ai_form.addRow(QLabel("Gesture stability duration (s):"), self.timer_dur)
        ai_card.layout.addLayout(ai_form)
        self.main_layout.addWidget(ai_card)

        # Save Button
        self.btn_save = QPushButton("Save Settings", self)
        self.btn_save.setObjectName("primary-btn")
        self.btn_save.setFixedWidth(140)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.main_layout.addWidget(self.btn_save)
        self.main_layout.addStretch()

    def _on_save_clicked(self):
        cam_idx = self.cam_dropdown.currentIndex()
        port = self.mav_port.text().strip()
        try:
            dur = float(self.timer_dur.text().strip())
        except ValueError:
            dur = 5.0
        self.settings_applied.emit(cam_idx, port, dur)
