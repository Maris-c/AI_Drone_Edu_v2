"""
MissionController — manages the Mission state machine.

Responsibilities:
  • Add gesture-generated blocks (with validation & merge)
  • Clear, export, import mission
  • Emit signals to drive the Mission Panel UI
"""
from __future__ import annotations
import json
from typing import List

from PySide6.QtCore import QObject, Signal

from models.mission import Mission
from models.block import MissionBlock
from services.mission_generator import MissionGenerator


class MissionController(QObject):
    # signals
    block_added        = Signal(object)        # MissionBlock
    block_updated      = Signal(int, object)   # index, updated MissionBlock
    mission_cleared    = Signal()
    mission_loaded     = Signal(list)          # List[MissionBlock]
    validation_warning = Signal(str)
    validation_cleared = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.mission  = Mission()
        self._gen     = MissionGenerator()

    # ------------------------------------------------------------------
    # Slot: called by GestureController.gesture_confirmed
    # ------------------------------------------------------------------
    def add_gesture(self, gesture_name: str) -> None:
        block = self._gen.generate(gesture_name)
        if block is None:
            return

        ok, warning = self.mission.validate_add(block)
        if not ok:
            self.validation_warning.emit(warning)
            return

        self.validation_cleared.emit()

        if self.mission.can_merge(block):
            idx  = len(self.mission.blocks) - 1
            last = self.mission.blocks[idx]
            last.repeat += 1
            self.block_updated.emit(idx, last)
        else:
            self.mission.blocks.append(block)
            self.block_added.emit(block)

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.mission.blocks.clear()
        self.mission_cleared.emit()
        self.validation_cleared.emit()

    def remove_block(self, idx: int) -> None:
        if 0 <= idx < len(self.mission.blocks):
            self.mission.blocks.pop(idx)
            self.mission_loaded.emit(self.mission.blocks)

    def update_block_params(self, idx: int, new_params: dict) -> None:
        if 0 <= idx < len(self.mission.blocks):
            block = self.mission.blocks[idx]
            block.params.update(new_params)
            self.block_updated.emit(idx, block)

    def reorder_block(self, old_idx: int, new_idx: int) -> None:
        if 0 <= old_idx < len(self.mission.blocks) and 0 <= new_idx <= len(self.mission.blocks):
            block = self.mission.blocks.pop(old_idx)
            # if moving down, the index shifted because we popped
            self.mission.blocks.insert(new_idx, block)
            self.mission_loaded.emit(self.mission.blocks)

    def blocks(self) -> List[MissionBlock]:
        return self.mission.blocks

    # ------------------------------------------------------------------
    # JSON I/O
    # ------------------------------------------------------------------
    def export_json(self) -> str:
        return self.mission.to_json()

    def import_json(self, text: str) -> tuple[bool, str]:
        try:
            items = json.loads(text)
            blocks: List[MissionBlock] = []
            for item in items:
                b = MissionGenerator.from_json_item(item)
                if b:
                    blocks.append(b)
            self.mission.blocks = blocks
            self.mission_loaded.emit(blocks)
            self.validation_cleared.emit()
            return True, f"Imported {len(blocks)} block(s)."
        except Exception as exc:
            return False, str(exc)
