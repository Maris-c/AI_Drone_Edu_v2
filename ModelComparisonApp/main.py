import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon

from ModelComparisonApp.ui import ModelComparisonUI

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI Drone Model Comparison")
    app.setStyle("Fusion")
    
    # Optional Icon
    icon_path = os.path.join(_ROOT, "icons", "drone.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Default font
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)

    win = ModelComparisonUI()
    win.setMinimumSize(900, 700)
    win.resize(1000, 800)
    win.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
