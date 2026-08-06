from PySide6.QtWidgets import QWidget, QVBoxLayout

class BasePage(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.page_title = title
        
        # Consistent layout padding (24px padding around pages)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)
        
    def get_title(self):
        return self.page_title
