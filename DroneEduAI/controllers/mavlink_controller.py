"""
MAVLinkController — Orchestrates MAVLinkService and maps MissionBlocks → MAVLink commands.

Maps the 9 gesture commands:
  TAKEOFF  → MAV_CMD_NAV_TAKEOFF (arm + GUIDED + climb)
  LAND     → MAV_CMD_NAV_LAND
  FORWARD  → SET_POSITION_TARGET_LOCAL_NED  vx=+speed
  BACKWARD → SET_POSITION_TARGET_LOCAL_NED  vx=-speed
  LEFT     → SET_POSITION_TARGET_LOCAL_NED  vy=-speed
  RIGHT    → SET_POSITION_TARGET_LOCAL_NED  vy=+speed
  UP       → SET_POSITION_TARGET_LOCAL_NED  vz=-vert  (NED: -Z = up)
  DOWN     → SET_POSITION_TARGET_LOCAL_NED  vz=+vert
  HOVER    → SET_POSITION_TARGET_LOCAL_NED  vx=vy=vz=0
"""
from __future__ import annotations
import time
from typing import List, Optional

from PySide6.QtCore import QObject, Signal, QThread

from models.block import MissionBlock
from services.mavlink_service import MAVLinkService


# Default motion parameters (configurable)
_DEFAULT_SPEED   = 1.0   # m/s lateral / longitudinal
_DEFAULT_VERT    = 0.5   # m/s vertical
_DEFAULT_ALT     = 3.0   # takeoff altitude (m)


# ── Velocity lookup for the 9 movement commands ───────────────────────────
_VEL_MAP: dict[str, tuple[float, float, float]] = {
    "FORWARD":  ( _DEFAULT_SPEED,  0,              0            ),
    "BACKWARD": (-_DEFAULT_SPEED,  0,              0            ),
    "LEFT":     ( 0,              -_DEFAULT_SPEED,  0            ),
    "RIGHT":    ( 0,               _DEFAULT_SPEED,  0            ),
    "UP":       ( 0,               0,              -_DEFAULT_VERT),  # NED: -Z = up
    "DOWN":     ( 0,               0,               _DEFAULT_VERT),
    "HOVER":    ( 0,               0,               0            ),
}


class MAVLinkController(QObject):
    """
    Public interface used by MissionBuilder + MissionPanel.
    Re-emits all signals from MAVLinkService so widgets don't need to import it.
    """

    # ── Signals ──────────────────────────────────────────────────────────
    connection_changed = Signal(bool, str)   # (connected, label)
    telemetry_updated  = Signal(dict)        # telemetry dict
    command_ack        = Signal(str)         # log line
    mission_progress   = Signal(int, int)    # (block_index, total)
    mission_finished   = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._service: Optional[MAVLinkService] = None
        self._connected = False
        self._worker: Optional[_MissionWorker] = None

    # ── Connection ────────────────────────────────────────────────────────
    def connect_to(self, connection_string: str) -> None:
        """Connect to MAVLink endpoint, e.g. 'udp:127.0.0.1:14550'."""
        self._teardown_service()

        self._service = MAVLinkService(self)
        self._service.connection_changed.connect(self._on_connection_changed)
        self._service.telemetry_updated.connect(self.telemetry_updated)
        self._service.command_ack.connect(self.command_ack)

        self._service.connect_to(connection_string)

    def disconnect(self) -> None:
        self._teardown_service()
        self.connection_changed.emit(False, "Disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # Backward-compat stub (called on startup by MissionBuilder)
    def connect_simulator(self) -> None:
        pass  # User connects via MAVLinkPanel UI

    # ── Mission execution ─────────────────────────────────────────────────
    def run_mission(self, blocks: List[MissionBlock]) -> None:
        if not self._service or not self._connected:
            self.command_ack.emit("✗ Not connected — open MAVLink panel and click Connect")
            return
        if not blocks:
            self.command_ack.emit("✗ Mission is empty")
            return

        # Stop any running worker
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(2000)

        self._worker = _MissionWorker(self._service, blocks)
        self._worker.log.connect(self.command_ack)
        self._worker.progress.connect(self.mission_progress)
        self._worker.finished.connect(self._on_mission_finished)
        self._worker.start()

    def stop_mission(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        if self._service:
            self._service.send_rtl()
        self.command_ack.emit("■ Mission STOPPED — RTL")

    # ── Single block (used by send_block stub) ────────────────────────────
    def send_block(self, block: MissionBlock) -> None:
        if not self._service or not self._connected:
            self.command_ack.emit(f"[STUB] {block.cmd} {block.params}")
            return
        vx, vy, vz = _VEL_MAP.get(block.cmd, (0, 0, 0))
        if block.cmd == "TAKEOFF":
            self._service.send_takeoff(block.params.get("alt", _DEFAULT_ALT))
        elif block.cmd == "LAND":
            self._service.send_land()
        else:
            self._service.send_velocity(vx, vy, vz)

    # ── Private ───────────────────────────────────────────────────────────
    def _on_connection_changed(self, ok: bool, label: str) -> None:
        self._connected = ok
        self.connection_changed.emit(ok, label)

    def _on_mission_finished(self) -> None:
        self.mission_finished.emit()

    def _teardown_service(self) -> None:
        if self._service:
            try:
                self._service.disconnect()
            except Exception:
                pass
            self._service = None
        self._connected = False


# ── Mission execution worker thread ──────────────────────────────────────
class _MissionWorker(QThread):
    """Executes a list of MissionBlocks sequentially in a background thread."""

    log      = Signal(str)
    progress = Signal(int, int)

    def __init__(self, svc: MAVLinkService, blocks: List[MissionBlock]):
        super().__init__()
        self._svc    = svc
        self._blocks = blocks
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        total = len(self._blocks)
        self.log.emit(f"▶ Mission started — {total} block(s)")

        for i, block in enumerate(self._blocks):
            if self._cancel:
                self.log.emit("■ Mission cancelled")
                return

            self.progress.emit(i, total)
            self._execute_block(i + 1, total, block)

        self.progress.emit(total, total)
        self.log.emit("✓ Mission complete")

    def _execute_block(self, idx: int, total: int, block: MissionBlock) -> None:
        cmd    = block.cmd
        params = block.params

        # ── TAKEOFF ───────────────────────────────────────────────────────
        if cmd == "TAKEOFF":
            alt = params.get("alt", _DEFAULT_ALT)
            self.log.emit(f"[{idx}/{total}] TAKEOFF → alt={alt}m")
            # 1. GUIDED mode
            self._svc.send_set_mode(4)
            self.log.emit("→ SET_MODE GUIDED")
            self._sleep(1.5)
            # 2. Arm
            self._svc.send_arm(True)
            self.log.emit("→ ARM")
            if not self._svc.wait_for_arm(timeout=12):
                self.log.emit("✗ Arm timeout (check pre-arm checks in SITL)")
                return
            self.log.emit("✓ Armed")
            self._sleep(0.5)
            # 3. Takeoff
            self._svc.send_takeoff(alt)
            if not self._svc.wait_for_altitude(alt * 0.8, timeout=25):
                self.log.emit(f"⚠ Altitude timeout (target {alt:.1f}m)")
            else:
                self.log.emit(f"✓ Reached ~{alt:.1f}m")
            self._sleep(2.0)

        # ── LAND ─────────────────────────────────────────────────────────
        elif cmd == "LAND":
            self.log.emit(f"[{idx}/{total}] LAND")
            self._svc.send_land()
            self._sleep(5.0)

        # ── Movement commands ─────────────────────────────────────────────
        elif cmd in _VEL_MAP:
            duration = params.get("duration", 2.0) * block.repeat
            vx, vy, vz = _VEL_MAP[cmd]
            dir_str = f"vx={vx:+.1f} vy={vy:+.1f} vz={vz:+.1f}"
            self.log.emit(f"[{idx}/{total}] {cmd} for {duration:.1f}s  ({dir_str})")

            # Send velocity in a loop for the duration
            deadline = time.time() + duration
            while time.time() < deadline and not self._cancel:
                self._svc.send_velocity(vx, vy, vz)
                time.sleep(0.15)

            # Hover to stop (unless already HOVER)
            if cmd != "HOVER":
                self._svc.send_velocity(0, 0, 0)
                self.log.emit(f"→ HOVER (stop after {cmd})")

        else:
            self.log.emit(f"[{idx}/{total}] Unknown command: {cmd}")

    def _sleep(self, seconds: float) -> None:
        """Interruptible sleep."""
        deadline = time.time() + seconds
        while time.time() < deadline and not self._cancel:
            time.sleep(0.05)
