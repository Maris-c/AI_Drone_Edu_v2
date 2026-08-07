"""
MissionGenerator — maps a gesture name to a MissionBlock.
Also exposes helpers for the Gesture Library UI widget.
"""
from __future__ import annotations
import os
from typing import List, Optional, Dict, Any

import config
from models.block import MissionBlock

# ---------------------------------------------------------------------------
# Gesture name → mission block spec
# ---------------------------------------------------------------------------
_GESTURE_MAP: Dict[str, Dict[str, Any]] = {
    "Takeoff":  {"cmd": "TAKEOFF",   "title": "Takeoff",       "params": {"alt": 1.5},       "block_type": "start"},
    "Land":     {"cmd": "LAND",      "title": "Land",          "params": {},                 "block_type": "end"},
    "Forward":  {"cmd": "FORWARD",   "title": "Forward",       "params": {"duration": 2},    "block_type": "movement"},
    "Backward": {"cmd": "BACKWARD",  "title": "Backward",      "params": {"duration": 2},    "block_type": "movement"},
    "Left":     {"cmd": "LEFT",      "title": "Move Left",     "params": {"duration": 2},    "block_type": "movement"},
    "Right":    {"cmd": "RIGHT",     "title": "Move Right",    "params": {"duration": 2},    "block_type": "movement"},
    "Up":       {"cmd": "UP",        "title": "Altitude Up",   "params": {"delta": 0.5},     "block_type": "movement"},
    "Down":     {"cmd": "DOWN",      "title": "Altitude Down", "params": {"delta": -0.5},    "block_type": "movement"},
    "Hover":    {"cmd": "HOVER",     "title": "Hover",         "params": {"duration": 3},    "block_type": "movement"},
}


class MissionGenerator:
    # ------------------------------------------------------------------
    def generate(self, gesture_name: str) -> Optional[MissionBlock]:
        """Create a MissionBlock from a confirmed gesture name."""
        spec = _GESTURE_MAP.get(gesture_name)
        if spec is None:
            return None
        cmd = spec["cmd"]
        return MissionBlock(
            cmd=cmd,
            title=spec["title"],
            params=spec["params"].copy(),
            icon_name=config.BLOCK_ICONS.get(cmd, ""),
            color=config.BLOCK_COLORS.get(cmd, config.COLOR_ACCENT),
            block_type=spec["block_type"],
        )

    # ------------------------------------------------------------------
    @staticmethod
    def icon_path(icon_name: str) -> str:
        return os.path.join(config.ICONS_DIR, f"{icon_name}.svg")

    # ------------------------------------------------------------------
    @staticmethod
    def all_gesture_info() -> List[Dict[str, str]]:
        """Return list of dicts for the Gesture Library grid."""
        result = []
        for gesture_name, spec in _GESTURE_MAP.items():
            cmd = spec["cmd"]
            icon_name = config.BLOCK_ICONS.get(cmd, "")
            result.append({
                "gesture_name": gesture_name,
                "title":        spec["title"],
                "icon_name":    icon_name,
                "icon_path":    MissionGenerator.icon_path(icon_name),
            })
        return result

    # ------------------------------------------------------------------
    @staticmethod
    def from_json_item(item: dict) -> Optional[MissionBlock]:
        """Reconstruct a MissionBlock from a JSON export dict."""
        cmd_to_gesture = {v["cmd"]: k for k, v in _GESTURE_MAP.items()}
        cmd = item.get("cmd", "")
        gesture = cmd_to_gesture.get(cmd)
        if not gesture:
            return None
        gen = MissionGenerator()
        block = gen.generate(gesture)
        if block and "repeat" in item:
            block.repeat = int(item["repeat"])
        return block
