from PySide6.QtWidgets import (QWidget, QLabel, QFormLayout, QLineEdit, 
                             QDoubleSpinBox, QVBoxLayout, QFrame, QPushButton)
from PySide6.QtCore import Signal, Qt
from app.widgets.card import Card

class BlockPropertiesPanel(Card):
    # Signals
    property_updated = Signal(str, float, str)  # block_id, new_duration, description

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setObjectName("properties_panel")
        self.setStyleSheet("""
            QFrame#properties_panel {
                background-color: #10111A;
                border-left: 1px solid #222536;
                border-radius: 0px; /* Flush against panel edge */
            }
        """)

        self.current_block_id = None
        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = self.layout
        self.main_layout.setContentsMargins(16, 20, 16, 16)
        self.main_layout.setSpacing(16)

        # Title
        self.title_lbl = QLabel("BLOCK PROPERTIES")
        self.title_lbl.setObjectName("secondary")
        self.title_lbl.setStyleSheet("font-weight: bold; letter-spacing: 1px;")
        self.main_layout.addWidget(self.title_lbl)

        # Placeholder Widget when no block is selected
        self.placeholder_widget = QWidget(self)
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setContentsMargins(0, 40, 0, 40)
        
        lbl_msg = QLabel("Select a programming block\nto view its properties")
        lbl_msg.setObjectName("secondary")
        lbl_msg.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(lbl_msg)
        
        self.main_layout.addWidget(self.placeholder_widget)

        # Editor Fields Container Widget
        self.editor_widget = QWidget(self)
        self.editor_layout = QVBoxLayout(self.editor_widget)
        self.editor_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        # Block Name Read-Only Display
        self.field_name = QLabel("-")
        self.field_name.setStyleSheet("font-weight: 600; color: #FFFFFF; font-size: 13px;")

        # Parameters: Duration
        self.field_duration = QDoubleSpinBox(self)
        self.field_duration.setRange(0.1, 60.0)
        self.field_duration.setSingleStep(0.5)
        self.field_duration.setSuffix(" sec")
        self.field_duration.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #08090d;
                border: 1px solid #32354c;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
        """)

        # Description
        self.field_desc = QLineEdit(self)
        self.field_desc.setStyleSheet("""
            QLineEdit {
                background-color: #08090d;
                border: 1px solid #32354c;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
        """)

        # Execution order
        self.field_order = QLabel("-")
        self.field_order.setStyleSheet("color: #00E5FF; font-weight: bold;")

        form.addRow(QLabel("Block Type:"), self.field_name)
        form.addRow(QLabel("Duration:"), self.field_duration)
        form.addRow(QLabel("Description:"), self.field_desc)
        form.addRow(QLabel("Exec Order:"), self.field_order)
        
        self.editor_layout.addLayout(form)

        # Update button
        self.btn_apply = QPushButton("Apply Parameters", self)
        self.btn_apply.setObjectName("primary-btn")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        self.editor_layout.addWidget(self.btn_apply)

        self.main_layout.addWidget(self.editor_widget)
        self.editor_widget.setVisible(False)

    def load_block_properties(self, block_model):
        """
        Populates fields with selected block metadata.
        """
        self.current_block_id = block_model.id
        
        self.field_name.setText(block_model.name)
        self.field_duration.setValue(block_model.duration)
        self.field_desc.setText(block_model.description)
        self.field_order.setText(f"#{block_model.execution_order}")

        # Disable duration for start/loop control headers
        is_action = block_model.name not in ["Mission Start", "Repeat While Active"]
        self.field_duration.setEnabled(is_action)

        self.placeholder_widget.setVisible(False)
        self.editor_widget.setVisible(True)

    def clear_selection(self):
        self.current_block_id = None
        self.placeholder_widget.setVisible(True)
        self.editor_widget.setVisible(False)

    def _on_apply_clicked(self):
        if self.current_block_id:
            dur = self.field_duration.value()
            desc = self.field_desc.text().strip()
            self.property_updated.emit(self.current_block_id, dur, desc)
