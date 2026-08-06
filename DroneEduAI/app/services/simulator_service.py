from PySide6.QtCore import QObject, Signal

class DroneSimulatorService(QObject):
    # Signals
    simulator_started = Signal()
    simulator_stopped = Signal()
    position_updated = Signal(float, float, float)  # x, y, z

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.drone_x = 0.0
        self.drone_y = 0.0
        self.drone_z = 0.0

    def start_simulator(self):
        """
        Starts the simulation engine loop.
        """
        self.is_running = True
        self.simulator_started.emit()
        print("Simulator Service: Running drone physics simulation.")

    def stop_simulator(self):
        """
        Stops the simulator.
        """
        self.is_running = False
        self.simulator_stopped.emit()
        print("Simulator Service: Stopped physics simulation.")

    def send_control_input(self, roll, pitch, yaw, thrust):
        """
        Receives pilot inputs and calculates physics reactions.
        """
        if not self.is_running:
            return
        # Simulating movement integration
        self.drone_x += roll * 0.1
        self.drone_y += pitch * 0.1
        self.drone_z += (thrust - 0.5) * 0.2
        self.position_updated.emit(self.drone_x, self.drone_y, self.drone_z)
