from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Slot, Qt, QTimer

from app.ui.top_bar import TopBar
from app.ui.status_bar import CustomStatusBar
from app.pages.mission_builder.mission_builder_page import MissionBuilderPage


class MainWindow(QMainWindow):
    """
    Simplified single-page shell.
    Layout: TopBar → MissionBuilderPage (full-width) → StatusBar
    No sidebar navigation – Mission Builder is the sole interface.
    """

    def __init__(self, camera_thread, mp_service,
                 telemetry_service, mavlink_service, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DroneEduAI – Mission Builder")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        self.camera_thread = camera_thread
        self.mp_service    = mp_service
        self.telemetry     = telemetry_service
        self.mavlink       = mavlink_service

        self._setup_ui()
        self._connect_signals()

        # Start background services
        self.telemetry.start_stream()
        self.mavlink.connect_drone()

    # ── UI ────────────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Top Header Bar
        self.top_bar = TopBar(self)
        layout.addWidget(self.top_bar)

        # 2. Mission Builder Page (fills remaining space)
        self.mission_page = MissionBuilderPage(
            camera_thread=self.camera_thread,
            mp_service=self.mp_service,
            parent=self,
        )
        layout.addWidget(self.mission_page, 1)

        # 3. Runtime Status Bar
        self.status_bar = CustomStatusBar(self)
        layout.addWidget(self.status_bar)

    # ── Signals ───────────────────────────────────────────────────────
    def _connect_signals(self):
        # Avatar dropdown
        self.top_bar.profile_clicked.connect(lambda: None)
        self.top_bar.logout_clicked.connect(self.close)

        # Telemetry → top bar + status bar
        self.telemetry.telemetry_updated.connect(self._on_telemetry_updated)

        # MAVLink state
        self.mavlink.connected.connect(self._on_mavlink_changed)

        # Camera FPS → status bar
        self.camera_thread.fps_updated.connect(self._on_fps_updated)

    # ── Slots ─────────────────────────────────────────────────────────
    @Slot(dict)
    def _on_telemetry_updated(self, data):
        self.top_bar.set_battery_level(data.get("battery", 100))
        self.status_bar.update_telemetry(self.telemetry.is_active)
        self.status_bar.update_simulator(self.camera_thread.isRunning())

    @Slot(bool)
    def _on_mavlink_changed(self, connected):
        self.top_bar.set_connection_status(connected)
        self.status_bar.update_mavlink(connected)

    @Slot(float)
    def _on_fps_updated(self, fps):
        self.status_bar.update_fps(fps)

    # ── Clean Shutdown ────────────────────────────────────────────────
    def closeEvent(self, event):
        self.camera_thread.stop()
        self.telemetry.stop_stream()
        super().closeEvent(event)
