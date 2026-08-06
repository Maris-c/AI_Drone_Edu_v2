import json
import uuid
from PySide6.QtCore import QObject, Signal


# ── Block Type Category Map ──────────────────────────────────────────
BLOCK_TYPE_MAP = {
    "Mission Start": "start",
    "Takeoff":       "takeoff",
    "Land":          "land",
    "Forward":       "move",
    "Backward":      "move",
    "Turn Right":    "move",
    "Turn Left":     "move",
    "Move Right":    "move",
    "Move Left":     "move",
    "Up":            "vertical",
    "Down":          "vertical",
    "Hover":         "hover",
}

# ── Block Type → Colour ──────────────────────────────────────────────
BLOCK_TYPE_COLORS = {
    "start":    "#22C55E",
    "takeoff":  "#8B5CF6",
    "land":     "#8B5CF6",
    "move":     "#3B82F6",
    "vertical": "#06B6D4",
    "hover":    "#F59E0B",
}

# ── Command Export Map ───────────────────────────────────────────────
CMD_MAP = {
    "Mission Start": "MISSION_START",
    "Takeoff":       "TAKEOFF",
    "Land":          "LAND",
    "Forward":       "FORWARD",
    "Backward":      "BACKWARD",
    "Turn Right":    "TURN_RIGHT",
    "Turn Left":     "TURN_LEFT",
    "Move Right":    "MOVE_RIGHT",
    "Move Left":     "MOVE_LEFT",
    "Up":            "UP",
    "Down":          "DOWN",
    "Hover":         "HOVER",
}

# ── Gesture → Block Name Map ─────────────────────────────────────────
GESTURE_BLOCK_MAP = {
    "Open Hand":   "Takeoff",
    "Fist":        "Land",
    "Takeoff":     "Takeoff",
    "Land":        "Land",
    "Forward":     "Forward",
    "Backward":    "Backward",
    "Turn Right":  "Turn Right",
    "Turn Left":   "Turn Left",
    "Move Right":  "Move Right",
    "Move Left":   "Move Left",
    "Up":          "Up",
    "Down":        "Down",
    "Hover":       "Hover",
}


class BlockModel:
    def __init__(self, id=None, name="Unknown", duration=2.0,
                 description="", parameters=None, repeat_count=1):
        self.id             = id or str(uuid.uuid4())[:8]
        self.name           = name
        self.duration       = duration
        self.description    = description if description else f"Execute {name} command."
        self.parameters     = parameters if parameters else {"duration": duration}
        self.repeat_count   = repeat_count
        self.execution_order = 0
        self.block_type     = BLOCK_TYPE_MAP.get(name, "move")
        self.color          = BLOCK_TYPE_COLORS.get(self.block_type, "#3B82F6")


class MissionModel(QObject):
    mission_changed  = Signal()
    block_added      = Signal(str)   # Emits block id of newly added / updated block
    validation_warn  = Signal(list)  # Emits list of warning strings

    def __init__(self):
        super().__init__()
        self.blocks: list[BlockModel] = []
        self.initialize_default_mission()

    # ── Initialise ───────────────────────────────────────────────────
    def initialize_default_mission(self):
        self.blocks = [
            BlockModel(
                id="start",
                name="Mission Start",
                duration=0.0,
                description="Initialization block. Triggers at mission launch.",
                repeat_count=1,
            ),
        ]
        self._reindex()

    # ── Add Block (with merge) ────────────────────────────────────────
    def add_block(self, gesture_name: str, duration: float = 2.0) -> BlockModel:
        """
        Maps gesture name → block name, then either merges with the last block
        (if it has the same type and isn't a control block) or appends a new one.
        """
        block_name = GESTURE_BLOCK_MAP.get(gesture_name, gesture_name)

        # Control blocks cannot be merged
        control_blocks = {"Mission Start"}

        # Check for merge with last non-start block
        if (self.blocks and
                block_name not in control_blocks and
                self.blocks[-1].name == block_name and
                self.blocks[-1].name not in control_blocks):
            # Merge: increment repeat_count, update duration
            last = self.blocks[-1]
            last.repeat_count += 1
            last.duration += duration
            last.parameters["duration"] = last.duration
            last.parameters["repeat"] = last.repeat_count
            self._reindex()
            self._validate_and_notify()
            self.mission_changed.emit()
            self.block_added.emit(last.id)
            return last
        else:
            # Append new block
            block_id = f"b_{len(self.blocks):03d}"
            new_block = BlockModel(
                id=block_id,
                name=block_name,
                duration=duration,
                repeat_count=1,
            )
            self.blocks.append(new_block)
            self._reindex()
            self._validate_and_notify()
            self.mission_changed.emit()
            self.block_added.emit(new_block.id)
            return new_block

    # ── Remove Block ─────────────────────────────────────────────────
    def remove_block(self, block_id: str):
        if block_id == "start":
            return  # Never remove Mission Start
        self.blocks = [b for b in self.blocks if b.id != block_id]
        self._reindex()
        self._validate_and_notify()
        self.mission_changed.emit()

    # ── Clear Mission ─────────────────────────────────────────────────
    def clear_mission(self):
        self.initialize_default_mission()
        self._validate_and_notify()
        self.mission_changed.emit()

    # ── Validate ──────────────────────────────────────────────────────
    def validate_mission(self) -> list[str]:
        """
        Returns a list of warning strings. Empty list = mission is valid.
        """
        warnings = []
        has_takeoff = False
        for block in self.blocks:
            if block.name == "Mission Start":
                continue
            if block.name == "Takeoff":
                has_takeoff = True
            elif block.block_type in ("move", "vertical", "hover") and not has_takeoff:
                warnings.append(
                    f"⚠  '{block.name}' at step #{block.execution_order}: "
                    "Takeoff is required before movement."
                )
        return warnings

    # ── Export JSON ───────────────────────────────────────────────────
    def export_json(self) -> str:
        """
        Exports the current mission as a JSON string matching the spec format.
        """
        payload = []
        for block in self.blocks:
            if block.name == "Mission Start":
                continue
            cmd = CMD_MAP.get(block.name, block.name.upper().replace(" ", "_"))
            entry = {
                "step":   block.execution_order,
                "cmd":    cmd,
                "name":   block.name,
                "time":   round(block.duration, 2),
                "repeat": block.repeat_count,
            }
            # Special params
            if block.name == "Takeoff":
                entry["alt"] = 1.5
            elif block.name in ("Up", "Down"):
                entry["dist"] = 1.0
            payload.append(entry)
        return json.dumps(payload, indent=2)

    # ── Import JSON ───────────────────────────────────────────────────
    def import_from_json(self, json_str: str) -> bool:
        """
        Parses a JSON string and rebuilds the mission block list.
        Returns True on success, False on error.
        """
        try:
            data = json.loads(json_str)
            self.blocks = [
                BlockModel(
                    id="start",
                    name="Mission Start",
                    duration=0.0,
                    description="Initialization block.",
                    repeat_count=1,
                )
            ]
            for entry in data:
                name = entry.get("name", "Hover")
                dur  = float(entry.get("time", 2.0))
                rep  = int(entry.get("repeat", 1))
                blk  = BlockModel(name=name, duration=dur, repeat_count=rep)
                self.blocks.append(blk)
            self._reindex()
            self.mission_changed.emit()
            return True
        except Exception as e:
            print(f"[MissionModel] import_from_json error: {e}")
            return False

    # ── Helpers ───────────────────────────────────────────────────────
    def _reindex(self):
        for idx, block in enumerate(self.blocks):
            block.execution_order = idx + 1

    def _validate_and_notify(self):
        warnings = self.validate_mission()
        self.validation_warn.emit(warnings)

    def reindex_execution_orders(self):
        self._reindex()
