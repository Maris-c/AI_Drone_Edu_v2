"""
DroneEduAI — Entry Point
"""
import sys
import os

# Put the DroneEduAI directory on sys.path so all absolute imports resolve.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Drone Edu AI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("STEAM UAV Lab")
    app.setStyle("Fusion")
    
    import config
    from PySide6.QtGui import QIcon
    icon_path = os.path.join(config.ICONS_DIR, "drone.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    if sys.platform == "win32":
        import ctypes
        myappid = 'steamuavlab.droneeduai.missionbuilder.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # Default font
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)

    win = MainWindow()
    win.setMinimumSize(800, 600)
    win.resize(1200, 800)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
