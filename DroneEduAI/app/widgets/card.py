from PySide6.QtWidgets import QFrame, QVBoxLayout

class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        
    def add_widget(self, widget):
        self.layout.addWidget(widget)
        
    def set_layout_margins(self, left, top, right, bottom):
        self.layout.setContentsMargins(left, top, right, bottom)
        
    def set_spacing(self, spacing):
        self.layout.setSpacing(spacing)
