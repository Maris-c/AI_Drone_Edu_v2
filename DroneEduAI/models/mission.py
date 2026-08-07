"""
Mission — ordered list of MissionBlocks with validation and serialization.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import json

from .block import MissionBlock

# Commands that require a prior TAKEOFF
_MOVEMENT_CMDS = {"FORWARD", "BACKWARD", "LEFT", "RIGHT", "UP", "DOWN", "HOVER", "LAND"}


@dataclass
class Mission:
    blocks: List[MissionBlock] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def has_takeoff(self) -> bool:
        return any(b.cmd == "TAKEOFF" for b in self.blocks)

    def is_airborne(self) -> bool:
        """True after TAKEOFF and before LAND."""
        airborne = False
        for b in self.blocks:
            if b.cmd == "TAKEOFF":
                airborne = True
            elif b.cmd == "LAND":
                airborne = False
        return airborne

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate_add(self, block: MissionBlock) -> Tuple[bool, str]:
        """Return (ok, warning_message)."""
        if block.cmd == "TAKEOFF":
            if self.has_takeoff() and self.is_airborne():
                return False, "⚠  Drone is already airborne — Land first."
        elif block.cmd in _MOVEMENT_CMDS:
            if not self.has_takeoff():
                return False, f"⚠  Takeoff is required before '{block.title}'."
        return True, ""

    def can_merge(self, block: MissionBlock) -> bool:
        """True if block should be merged with the last existing block."""
        if not self.blocks:
            return False
        last = self.blocks[-1]
        # Only merge identical repeatable movement commands
        return (last.cmd == block.cmd
                and block.cmd not in ("TAKEOFF", "LAND"))

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps([b.to_dict() for b in self.blocks], indent=2)
