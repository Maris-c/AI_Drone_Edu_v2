"""
MAVLinkService — QThread managing real pymavlink bidirectional communication.

OUT → MAV_CMD_NAV_TAKEOFF, MAV_CMD_NAV_LAND, SET_POSITION_TARGET_LOCAL_NED
IN  ← HEARTBEAT, ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS, VFR_HUD, COMMAND_ACK
"""
from __future__ import annotations
import time
import math
from typing import Optional

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

try:
    from pymavlink import mavutil
    _PYMAVLINK_OK = True
except ImportError:
    _PYMAVLINK_OK = False


class MAVLinkService(QThread):
    """Background thread: handles receive loop + exposes command methods."""

    # Signals (emitted from thread; picked up by Qt event loop)
    telemetry_updated  = Signal(dict)      # GPS, alt, battery, attitude, speed, mode, armed
    connection_changed = Signal(bool, str) # (connected, label)
    command_ack        = Signal(str)       # human-readable ACK / log line
    mission_progress   = Signal(int, int)  # (block_index, total)

    _TELEMETRY_HZ = 5
    _HEARTBEAT_TIMEOUT = 5.0  # seconds before "lost connection"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connection_string = ""
        self._mav               = None
        self._running           = False
        self._connected         = False
        self._mutex             = QMutex()

        # Telemetry state
        self._mode  = "—"
        self._armed = False
        self._bat   = -1
        self._alt   = 0.0
        self._lat   = 0.0
        self._lon   = 0.0
        self._speed = 0.0
        self._roll  = 0.0
        self._pitch = 0.0
        self._yaw   = 0.0
        self._last_hb = 0.0

    # ── Connection control (called from main thread) ──────────────────────
    def connect_to(self, connection_string: str) -> None:
        self._connection_string = connection_string
        if not self.isRunning():
            self._running = True
            self.start()

    def disconnect(self) -> None:
        self._running = False
        self.wait(4000)

    def is_connected(self) -> bool:
        return self._connected

    # ── QThread entry point ───────────────────────────────────────────────
    def run(self) -> None:
        if not _PYMAVLINK_OK:
            self.connection_changed.emit(False, "pymavlink not installed — run: pip install pymavlink")
            return

        # ------------------------------------------------------------------
        # Open connection
        # ------------------------------------------------------------------
        try:
            self.connection_changed.emit(False, "Connecting…")
            self._mav = mavutil.mavlink_connection(
                self._connection_string,
                autoreconnect=True,
                source_system=255,
                source_component=0,
            )
        except Exception as exc:
            self.connection_changed.emit(False, f"Open error: {exc}")
            return

        # Wait for first heartbeat (up to 10 s)
        try:
            hb = self._mav.wait_heartbeat(timeout=10)
        except Exception:
            hb = None

        if hb is None:
            self.connection_changed.emit(False, "Timeout — no heartbeat received")
            self._mav.close()
            return

        self._connected = True
        self._last_hb   = time.time()
        self._update_mode_from_hb(hb)
        self.connection_changed.emit(True, "Connected")
        self.command_ack.emit(
            f"✓ Heartbeat received from sys={self._mav.target_system} "
            f"comp={self._mav.target_component}"
        )

        # Request all data streams at 4 Hz
        self._request_streams()

        # ------------------------------------------------------------------
        # Main receive loop
        # ------------------------------------------------------------------
        interval   = 1.0 / self._TELEMETRY_HZ
        last_emit  = 0.0

        while self._running:
            try:
                msg = self._mav.recv_match(blocking=False, timeout=0.02)
                if msg:
                    self._handle_msg(msg)
            except Exception:
                pass

            now = time.time()

            # Emit telemetry at configured rate
            if now - last_emit >= interval:
                self._emit_telemetry()
                last_emit = now

            # Detect connection loss
            if now - self._last_hb > self._HEARTBEAT_TIMEOUT and self._connected:
                self._connected = False
                self.connection_changed.emit(False, "Connection lost (heartbeat timeout)")

            time.sleep(0.01)

        # ------------------------------------------------------------------
        # Cleanup
        # ------------------------------------------------------------------
        try:
            self._mav.close()
        except Exception:
            pass
        self._connected = False
        self.connection_changed.emit(False, "Disconnected")

    # ── Message dispatch ──────────────────────────────────────────────────
    def _handle_msg(self, msg) -> None:
        mtype = msg.get_type()

        if mtype == "HEARTBEAT":
            self._last_hb = time.time()
            if not self._connected:
                self._connected = True
                self.connection_changed.emit(True, "MAVLink connection restored")
            self._update_mode_from_hb(msg)

        elif mtype == "SYS_STATUS":
            if msg.battery_remaining >= 0:
                self._bat = msg.battery_remaining

        elif mtype == "GLOBAL_POSITION_INT":
            self._lat  = msg.lat    / 1e7
            self._lon  = msg.lon    / 1e7
            self._alt  = msg.relative_alt / 1000.0   # mm → m

        elif mtype == "GPS_RAW_INT":
            if self._lat == 0.0:        # fallback if GLOBAL_POSITION_INT absent
                self._lat = msg.lat / 1e7
                self._lon = msg.lon / 1e7

        elif mtype == "VFR_HUD":
            self._speed = msg.groundspeed
            if self._alt == 0.0:
                self._alt = msg.alt

        elif mtype == "ATTITUDE":
            self._roll  = math.degrees(msg.roll)
            self._pitch = math.degrees(msg.pitch)
            self._yaw   = math.degrees(msg.yaw)

        elif mtype == "COMMAND_ACK":
            results = {
                0: "✓ OK",
                1: "✗ Unsupported",
                2: "✗ Denied",
                3: "⏳ In Progress",
                4: "✗ Failed",
                5: "✗ Cancelled",
            }
            result_str = results.get(msg.result, f"result={msg.result}")
            cmd_name   = self._cmd_name(msg.command)
            self.command_ack.emit(f"← ACK {cmd_name}: {result_str}")

    def _update_mode_from_hb(self, msg) -> None:
        """Decode ArduCopter flight mode + armed state from HEARTBEAT."""
        copter_modes = {
            0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
            4: "GUIDED",    5: "LOITER", 6: "RTL",     7: "CIRCLE",
            9: "LAND",      11: "DRIFT", 13: "SPORT",  14: "FLIP",
            15: "AUTOTUNE", 16: "POSHOLD", 17: "BRAKE",
        }
        self._mode  = copter_modes.get(msg.custom_mode, f"MODE_{msg.custom_mode}")
        self._armed = bool(msg.base_mode & 0x80)   # MAV_MODE_FLAG_SAFETY_ARMED

    def _emit_telemetry(self) -> None:
        self.telemetry_updated.emit({
            "mode":    self._mode,
            "armed":   self._armed,
            "battery": self._bat,
            "alt":     round(self._alt, 1),
            "lat":     round(self._lat, 6),
            "lon":     round(self._lon, 6),
            "speed":   round(self._speed, 1),
            "roll":    round(self._roll, 1),
            "pitch":   round(self._pitch, 1),
            "yaw":     round(self._yaw, 1),
        })

    def _request_streams(self) -> None:
        if not self._mav:
            return
        try:
            self._mav.mav.request_data_stream_send(
                self._mav.target_system,
                self._mav.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL,
                4, 1
            )
        except Exception:
            pass

    # ── Command methods (thread-safe: pymavlink socket is thread-safe) ────

    def send_set_mode(self, mode_id: int) -> None:
        """Set ArduCopter flight mode by integer ID."""
        if not self._mav:
            return
        self._mav.mav.command_long_send(
            self._mav.target_system, self._mav.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            float(mode_id), 0, 0, 0, 0, 0
        )

    def send_arm(self, arm: bool = True) -> None:
        if not self._mav:
            return
        self._mav.mav.command_long_send(
            self._mav.target_system, self._mav.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0,
            1.0 if arm else 0.0,
            0, 0, 0, 0, 0, 0
        )

    def send_takeoff(self, alt: float = 3.0) -> None:
        if not self._mav:
            return
        self._mav.mav.command_long_send(
            self._mav.target_system, self._mav.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0,
            0, 0, 0, 0, 0, 0, alt
        )
        self.command_ack.emit(f"→ TAKEOFF alt={alt}m")

    def send_land(self) -> None:
        if not self._mav:
            return
        self._mav.mav.command_long_send(
            self._mav.target_system, self._mav.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND, 0,
            0, 0, 0, 0, 0, 0, 0
        )
        self.command_ack.emit("→ LAND")

    def send_velocity(self, vx: float, vy: float, vz: float) -> None:
        """
        Body-frame velocity command via SET_POSITION_TARGET_LOCAL_NED.
        vx = forward/backward,  vy = right/left,  vz = down/up (NED sign)
        """
        if not self._mav:
            return
        # type_mask: ignore position + acceleration + yaw; use velocity only
        type_mask = (0x0FC7)   # bit-mask: ignore x,y,z pos; use vx,vy,vz
        self._mav.mav.set_position_target_local_ned_send(
            0,
            self._mav.target_system, self._mav.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            type_mask,
            0, 0, 0,       # x, y, z position (ignored)
            vx, vy, vz,    # velocity
            0, 0, 0,       # acceleration (ignored)
            0, 0           # yaw, yaw_rate (ignored)
        )

    def send_rtl(self) -> None:
        """Return to Launch (mode 6)."""
        self.send_set_mode(6)
        self.command_ack.emit("→ RTL (Return to Launch)")

    # ── Blocking helpers (called from mission worker thread) ─────────────
    def wait_for_arm(self, timeout: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self._armed:
                return True
            time.sleep(0.1)
        return False

    def wait_for_altitude(self, target: float, tol: float = 0.5, timeout: float = 20.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if abs(self._alt - target) <= tol:
                return True
            time.sleep(0.2)
        return False

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _cmd_name(cmd_id: int) -> str:
        names = {
            22:  "TAKEOFF",
            21:  "LAND",
            400: "ARM/DISARM",
            176: "SET_MODE",
            84:  "SET_POSITION_TARGET",
        }
        return names.get(cmd_id, str(cmd_id))

    @property
    def pymavlink_available(self) -> bool:
        return _PYMAVLINK_OK
