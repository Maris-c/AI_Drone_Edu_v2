from PySide6.QtWidgets import QFrame, QVBoxLayout, QButtonGroup, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Signal, Qt
from app.widgets.icon_button import SidebarButton

class SidebarNavigation(QFrame):
    page_changed = Signal(str)  # Emits target page name key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 24, 12, 16)
        self.layout.setSpacing(8)

        # 1. Branding Header
        self.logo_label = QLabel("DRONEEDU AI")
        self.logo_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 2px;
            padding-left: 12px;
            padding-bottom: 24px;
        """)
        self.layout.addWidget(self.logo_label)

        # Button Group for navigation items
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        # 2. Main Navigation Items
        self.nav_items = [
            ("Dashboard", "dashboard", "dashboard"),
            ("Code", "mission-builder", "mission_builder"),  # User request: Mission Builder page (labeled "Code" in graphic)
            ("Simulator", "simulator", "simulator"),
            ("Reports", "reports", "reports"),
        ]

        self.buttons = {}
        for text, icon, page_key in self.nav_items:
            btn = SidebarButton(text, icon, self)
            self.btn_group.addButton(btn)
            self.layout.addWidget(btn)
            self.buttons[page_key] = btn

        # Spacer to push settings to the bottom
        self.layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 3. Settings Item (at the bottom)
        self.settings_btn = SidebarButton("Settings", "settings", self)
        self.btn_group.addButton(self.settings_btn)
        self.layout.addWidget(self.settings_btn)
        self.buttons["settings"] = self.settings_btn

        # Signals
        self.btn_group.buttonClicked.connect(self._on_button_clicked)

        # Set default selection
        self.buttons["mission_builder"].setChecked(True)

    def _on_button_clicked(self, button):
        for page_key, btn in self.buttons.items():
            if btn == button:
                self.page_changed.emit(page_key)
                break

    def navigate_to(self, page_key):
        """
        Manually select a navigation item in the sidebar.
        """
        if page_key in self.buttons:
            self.buttons[page_key].setChecked(True)
            self.page_changed.emit(page_key)
