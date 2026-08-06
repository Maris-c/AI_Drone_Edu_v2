from PySide6.QtWidgets import QLabel
from app.pages.base_page import BasePage
from app.widgets.card import Card

class ModelPage(BasePage):
    def __init__(self, parent=None):
        super().__init__("Model Manager", parent)
        card = Card(self)
        card.layout.addWidget(QLabel("Model Manager / Classifier Training placeholder."))
        self.main_layout.addWidget(card)
        self.main_layout.addStretch()
