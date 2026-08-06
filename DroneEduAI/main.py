import sys
import os

# Align python sys path to include app directory structure
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from app.themes.theme_manager import ThemeManager
from app.ui.main_window import MainWindow
from app.services.camera_service import CameraThread
from app.services.mediapipe_service import MediaPipeService
from app.services.telemetry_service import TelemetryService
from app.services.mavlink_service import MAVLinkService


def main():
    # 1. Initialise QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("DroneEduAI")
    app.setApplicationVersion("1.0.0")

    # 2. Apply dark stylesheet
    ThemeManager.apply_theme(app)

    # 3. Instantiate global services
    camera_thread     = CameraThread(camera_index=0)
    mp_service        = MediaPipeService()
    telemetry_service = TelemetryService()
    mavlink_service   = MAVLinkService()

    # 4. Build & show the main window (single-page Mission Builder)
    window = MainWindow(
        camera_thread=camera_thread,
        mp_service=mp_service,
        telemetry_service=telemetry_service,
        mavlink_service=mavlink_service,
    )
    window.show()

    # Test-mode: fast boot validation
    if "--test-mode" in sys.argv:
        print("Test mode: processing events…")
        QApplication.processEvents()
        camera_thread.stop()
        telemetry_service.stop_stream()
        mavlink_service.disconnect_drone()
        print("Test mode: OK – exiting.")
        return 0

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
