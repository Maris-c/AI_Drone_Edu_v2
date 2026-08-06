from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygon
from PySide6.QtCore import Qt, QSize, QPoint

class SidebarButton(QPushButton):
    def __init__(self, text, icon_type, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.icon_type = icon_type.lower()
        self.setCheckable(True)
        self.setMinimumHeight(44)
        
        # Stylesheet styling for active/inactive sidebar buttons
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #8E94B2;
                font-weight: 500;
                text-align: left;
                padding-left: 48px;
            }
            QPushButton:hover {
                background-color: rgba(124, 77, 255, 0.08);
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: rgba(124, 77, 255, 0.15);
                color: #00E5FF;
                font-weight: 600;
            }
        """)

    def paintEvent(self, event):
        # Let parent draw background text
        super().paintEvent(event)
        
        # Draw vector icon overlay
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Determine color based on states
        if self.isChecked():
            color = QColor("#00E5FF")
        elif self.underMouse():
            color = QColor("#FFFFFF")
        else:
            color = QColor("#8E94B2")
            
        painter.setPen(QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        
        # Icon dimensions: 18x18 bounding box centered at x=20
        x = 18
        y = (self.height() - 18) // 2
        
        if self.icon_type == "dashboard":
            # Grid of 4 small squares
            painter.drawRect(x, y, 7, 7)
            painter.drawRect(x + 10, y, 7, 7)
            painter.drawRect(x, y + 10, 7, 7)
            painter.drawRect(x + 10, y + 10, 7, 7)
            
        elif self.icon_type == "mission-builder" or self.icon_type == "code":
            # Angle brackets < > or block puzzle
            poly1 = QPolygon([
                QPoint(x + 6, y + 3),
                QPoint(x + 1, y + 9),
                QPoint(x + 6, y + 15)
            ])
            poly2 = QPolygon([
                QPoint(x + 12, y + 3),
                QPoint(x + 17, y + 9),
                QPoint(x + 12, y + 15)
            ])
            painter.drawPolyline(poly1)
            painter.drawPolyline(poly2)
            painter.drawLine(x + 11, y + 3, x + 7, y + 15)
            
        elif self.icon_type == "simulator":
            # Quadcopter cross layout
            painter.drawLine(x + 2, y + 2, x + 16, y + 16)
            painter.drawLine(x + 16, y + 2, x + 2, y + 16)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(x + 7, y + 7, 4, 4)
            # Propellers
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(x, y, 4, 4)
            painter.drawEllipse(x + 14, y, 4, 4)
            painter.drawEllipse(x, y + 14, 4, 4)
            painter.drawEllipse(x + 14, y + 14, 4, 4)
            
        elif self.icon_type == "reports":
            # Bar chart
            painter.drawLine(x, y + 16, x + 18, y + 16) # bottom line
            painter.drawRect(x + 2, y + 8, 3, 8)
            painter.drawRect(x + 7, y + 3, 3, 13)
            painter.drawRect(x + 12, y + 11, 3, 5)
            
        elif self.icon_type == "settings":
            # Gear
            painter.drawEllipse(x + 4, y + 4, 10, 10)
            painter.drawEllipse(x + 7, y + 7, 4, 4)
            # Teeth
            for i in range(8):
                angle = i * 45
                painter.save()
                painter.translate(x + 9, y + 9)
                painter.rotate(angle)
                painter.drawLine(0, -5, 0, -8)
                painter.restore()
                
        painter.end()


class FloatingActionButton(QPushButton):
    def __init__(self, text, is_run=True, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.is_run = is_run
        self.setFixedSize(150, 48)
        
        if is_run:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #00E676;
                    border: none;
                    border-radius: 24px;
                    color: #0B0C10;
                    font-size: 14px;
                    font-weight: bold;
                    padding-left: 20px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #69f0ae;
                }
                QPushButton:pressed {
                    background-color: #00c853;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FF1744;
                    border: none;
                    border-radius: 24px;
                    color: #FFFFFF;
                    font-size: 14px;
                    font-weight: bold;
                    padding-left: 20px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
                QPushButton:pressed {
                    background-color: #d50000;
                }
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.is_run:
            # Draw green play triangle
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#0B0C10")))
            points = QPolygon([
                QPoint(self.width() - 35, 17),
                QPoint(self.width() - 35, 31),
                QPoint(self.width() - 23, 24)
            ])
            painter.drawPolygon(points)
        else:
            # Draw white stop square
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRect(self.width() - 34, 18, 12, 12)
            
        painter.end()
