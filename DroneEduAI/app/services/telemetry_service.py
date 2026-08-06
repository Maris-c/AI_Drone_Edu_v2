from PySide6.QtCore import QObject, Signal, QTimer
import random
import math

class TelemetryService(QObject):
    # Signals
    telemetry_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._generate_telemetry)
        
        # Initial telemetry state
        self.altitude = 0.0
        self.battery = 100
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        self.speed = 0.0
        self.lat = -6.2088
        self.lon = 106.8456
        self.is_active = False

    def start_stream(self):
        """
        Starts emitting simulated drone telemetry.
        """
        self.is_active = True
        self.timer.start(200) # 5 Hz refresh rate

    def stop_stream(self):
        """
        Stops emitting telemetry.
        """
        self.is_active = False
        self.timer.stop()

    def _generate_telemetry(self):
        if not self.is_active:
            return
            
        # Add random walk fluctuations for drone simulation
        self.altitude = max(0.0, self.altitude + random.uniform(-0.1, 0.15))
        self.speed = max(0.0, self.speed + random.uniform(-0.2, 0.3))
        
        # Attitude variations
        self.pitch = 5.0 * math.sin(time_factor := random.random())
        self.roll = 3.0 * math.cos(time_factor)
        self.yaw = (self.yaw + random.uniform(-0.5, 0.5)) % 360
        
        # Slow battery depletion
        self.battery = max(0, self.battery - random.choice([0, 0, 1]))
        
        # Lat/Lon drift
        self.lat += random.uniform(-0.0001, 0.0001)
        self.lon += random.uniform(-0.0001, 0.0001)

        data = {
            "altitude": round(self.altitude, 2),
            "battery": self.battery,
            "pitch": round(self.pitch, 1),
            "roll": round(self.roll, 1),
            "yaw": round(self.yaw, 1),
            "speed": round(self.speed, 2),
            "gps": f"{round(self.lat, 5)}, {round(self.lon, 5)}",
            "satellites": random.randint(10, 18),
            "signal_rssi": random.randint(85, 99)
        }
        self.telemetry_updated.emit(data)
