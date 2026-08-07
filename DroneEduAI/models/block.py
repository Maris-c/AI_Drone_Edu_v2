"""
MissionBlock — the atom of a drone mission.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class MissionBlock:
    cmd: str                          # e.g. "TAKEOFF", "FORWARD"
    title: str                        # display name
    params: Dict[str, Any] = field(default_factory=dict)
    icon_name: str = ""               # stem of SVG file in /icons/
    color: str = "#8B5CF6"            # accent color for this block
    block_type: str = "movement"      # "start" | "movement" | "end"
    repeat: int = 1                   # merge counter

    # ------------------------------------------------------------------
    def get_param_text(self) -> str:
        """Human-readable summary of the block's parameters."""
        if self.repeat > 1:
            base = self._base_param()
            return f"Repeat × {self.repeat}  |  {base}" if base else f"Repeat × {self.repeat}"
        return self._base_param()

    def _base_param(self) -> str:
        if "alt" in self.params:
            return f"Altitude = {self.params['alt']}m"
        if "duration" in self.params:
            total = self.params["duration"] * self.repeat if self.repeat > 1 else self.params["duration"]
            return f"Duration = {total}s"
        if "delta" in self.params:
            sign = "+" if self.params["delta"] > 0 else ""
            return f"Delta = {sign}{self.params['delta']}m"
        return ""

    def get_tag(self) -> str:
        """Block type tag shown inside the card."""
        tags = {
            "start": "MISSION START",
            "end":   "MISSION END",
            "movement": "GESTURE",
        }
        return tags.get(self.block_type, "GESTURE")

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        result = {"cmd": self.cmd}
        result.update(self.params)
        if self.repeat > 1:
            result["repeat"] = self.repeat
        return result
