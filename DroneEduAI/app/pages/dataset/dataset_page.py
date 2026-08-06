from PySide6.QtWidgets import QLabel
from app.pages.base_page import BasePage
from app.widgets.card import Card

class DatasetPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("Dataset Collector", parent)
        card = Card(self)
        card.layout.addWidget(QLabel("Dataset Collector workspace placeholder."))
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()
