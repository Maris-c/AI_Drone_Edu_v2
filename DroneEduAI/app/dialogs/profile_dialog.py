from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTabWidget, QWidget
from PySide6.QtCore import Qt

class ProfileDialog(QDialog):
    def __init__(self, tab_index=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DroneEduAI - Account Panel")
        self.setFixedSize(400, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Style Dialog dark
        self.setStyleSheet("""
            QDialog {
                background-color: #10111A;
                border: 1px solid #222536;
            }
            QTabWidget::pane {
                border: 1px solid #222536;
                background-color: #151622;
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background: #10111A;
                color: #8E94B2;
                border: 1px solid #222536;
                border-bottom: none;
                padding: 6px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #151622;
                color: #FFFFFF;
                font-weight: bold;
            }
            QLabel {
                color: #EEFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Tab Widget
        tabs = QTabWidget(self)

        # 1. Profile Tab
        tab_profile = QWidget()
        prof_layout = QVBoxLayout(tab_profile)
        prof_layout.setContentsMargins(16, 16, 16, 16)
        prof_layout.setSpacing(8)

        lbl_avatar = QLabel("AV", self)
        lbl_avatar.setFixedSize(50, 50)
        lbl_avatar.setAlignment(Qt.AlignCenter)
        lbl_avatar.setStyleSheet("""
            background-color: #7C4DFF;
            color: #FFFFFF;
            border-radius: 25px;
            font-size: 18px;
            font-weight: bold;
        """)

        lbl_name = QLabel("Operator 01 (Admin)")
        lbl_name.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        lbl_role = QLabel("Role: UAV Lead Engineer")
        lbl_role.setStyleSheet("color: #8E94B2;")
        
        lbl_stats = QLabel("Recorded Gestures: 1,240 | Saved Missions: 14")
        lbl_stats.setStyleSheet("color: #00E5FF; font-size: 11px;")

        avatar_row = QHBoxLayout()
        avatar_row.addWidget(lbl_avatar)
        
        info_col = QVBoxLayout()
        info_col.addWidget(lbl_name)
        info_col.addWidget(lbl_role)
        avatar_row.addLayout(info_col)
        avatar_row.addStretch()

        prof_layout.addLayout(avatar_row)
        prof_layout.addWidget(lbl_stats)
        prof_layout.addStretch()
        tabs.addTab(tab_profile, "Profile")

        # 2. Preferences Tab
        tab_pref = QWidget()
        pref_layout = QVBoxLayout(tab_pref)
        pref_layout.setContentsMargins(16, 16, 16, 16)
        pref_layout.addWidget(QLabel("● Enable sound cues on block confirmed"))
        pref_layout.addWidget(QLabel("● Auto-save mission sequence history"))
        pref_layout.addWidget(QLabel("● Render GPU accelerated shaders"))
        pref_layout.addStretch()
        tabs.addTab(tab_pref, "Preferences")

        # 3. About Tab
        tab_about = QWidget()
        about_layout = QVBoxLayout(tab_about)
        about_layout.setContentsMargins(16, 16, 16, 16)
        
        about_title = QLabel("DroneEduAI - Platform V1.0")
        about_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        about_body = QLabel(
            "An AI-powered drone development platform integrating OpenCV camera loops, "
            "MediaPipe hand tracking classifiers, and custom visual node programming drag & drop layouts.\n\n"
            "Developed using PySide6 (Qt for Python)."
        )
        about_body.setWordWrap(True)
        about_body.setStyleSheet("color: #8E94B2; font-size: 12px; line-height: 18px;")

        about_layout.addWidget(about_title)
        about_layout.addWidget(about_body)
        about_layout.addStretch()
        tabs.addTab(tab_about, "About")

        # Select tab based on index
        tabs.setCurrentIndex(tab_index)
        layout.addWidget(tabs)

        # Close button
        btn_close = QPushButton("Dismiss", self)
        btn_close.setObjectName("primary-btn")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignRight)
