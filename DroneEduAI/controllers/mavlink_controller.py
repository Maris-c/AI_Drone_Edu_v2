"""
MAVLinkController — simulator stub.
Logs commands to console; real pymavlink can be wired in later.
"""
from __future__ import annotations
from PySide6.QtCore import QObject, Signal
from models.block import MissionBlock


class MAVLinkController(QObject):
    connection_changed = Signal(bool, str)   # connected, status_text
    command_sent       = Signal(str)         # human-readable command log

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._connected = False

    # ------------------------------------------------------------------
    def connect_simulator(self) -> None:
        self._connected = True
        self.connection_changed.emit(True, "Simulator")
        print("[MAVLink] Connected to simulator.")

    def disconnect(self) -> None:
        self._connected = False
        self.connection_changed.emit(False, "Disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    def send_block(self, block: MissionBlock) -> None:
        """Stub: print command and emit signal."""
        txt = f"{block.cmd}  {block.params}"
        print(f"[MAVLink STUB] {txt}")
        self.command_sent.emit(txt)

    def run_mission(self, blocks: list) -> None:
        print(f"[MAVLink STUB] Mission started — {len(blocks)} block(s):")
        for i, b in enumerate(blocks):
            print(f"  [{i+1:02d}] {b.cmd}  {b.params}  (×{b.repeat})")
        self.command_sent.emit(f"Mission running — {len(blocks)} blocks")

    def stop_mission(self) -> None:
        print("[MAVLink STUB] Mission STOP issued.")
        self.command_sent.emit("Mission STOPPED")
