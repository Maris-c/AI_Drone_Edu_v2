from PySide6.QtCore import QObject, Signal, QTimer
import random

class MAVLinkService(QObject):
    # Signals
    connected = Signal(bool)
    armed = Signal(bool)
    message_received = Signal(str)
    heartbeat_received = Signal(int) # RSSI or latency

    def __init__(self):
        super().__init__()
        self._connected = False
        self._armed = False
        
        # Simple simulated heartbeats
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self._on_heartbeat)
        
    def connect_drone(self, port="udp:127.0.0.1:14550"):
        """
        Simulate connection to the drone via MAVLink.
        """
        print(f"Connecting to drone MAVLink on port: {port}")
        self._connected = True
        self.connected.emit(True)
        self.heartbeat_timer.start(1000)
        self.message_received.emit("MAVLink: Connected to UAV.")
        return True

    def disconnect_drone(self):
        """
        Simulate disconnect.
        """
        print("Disconnecting from MAVLink...")
        self._connected = False
        self._armed = False
        self.heartbeat_timer.stop()
        self.connected.emit(False)
        self.armed.emit(False)
        self.message_received.emit("MAVLink: Disconnected.")

    def arm_drone(self):
        """
        Simulate ARM sequence.
        """
        if self._connected:
            self._armed = True
            self.armed.emit(True)
            self.message_received.emit("MAVLink: Drone Armed!")
            return True
        return False

    def disarm_drone(self):
        """
        Simulate DISARM sequence.
        """
        if self._connected:
            self._armed = False
            self.armed.emit(False)
            self.message_received.emit("MAVLink: Drone Disarmed.")
            return True
        return False

    def send_mission_item(self, command, params):
        """
        Placeholder to send MAVLink commands (e.g. MAV_CMD_NAV_TAKEOFF).
        """
        print(f"MAVLink Sending Command: {command} with params {params}")
        self.message_received.emit(f"MAVLink Sent Cmd: {command}")

    def _on_heartbeat(self):
        if self._connected:
            latency = random.randint(5, 25)
            self.heartbeat_received.emit(latency)
