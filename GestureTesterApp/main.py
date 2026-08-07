import os
import sys

def launch_gui():
    """Launches the PySide6 MediaPipe Model Tester GUI Application."""
    from PySide6.QtWidgets import QApplication
    from ui_window import GestureTesterWindow

    app = QApplication(sys.argv)
    window = GestureTesterWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    if "--cli" in sys.argv:
        from tester_engine import ModelTesterEngine
        engine = ModelTesterEngine()
        success, msg = engine.load_model()
        if not success:
            print(f"CLI Mode Error: {msg}")
        else:
            print(f"CLI Mode Ready: {msg}")
    else:
        launch_gui()
