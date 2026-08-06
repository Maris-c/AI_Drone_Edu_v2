"""
MissionValidator
────────────────
Stateless service that validates a block list against mission logic rules.
Returns a list of human-readable warning strings (empty = mission is valid).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.mission_model import BlockModel


class MissionValidator:

    # Blocks that require Takeoff to have appeared before them
    MOVEMENT_TYPES = {"move", "vertical", "hover"}
    # Blocks that are "control" and have no ordering requirement
    CONTROL_BLOCKS = {"Mission Start"}

    @staticmethod
    def validate(blocks: list["BlockModel"]) -> list[str]:
        """
        Runs all validation rules on the provided block list.

        Rules
        -----
        1. Movement/Hover blocks must come after a Takeoff block.
        2. A Land block should not appear before a Takeoff block.
        3. (Future) Mission must end with Land if started with Takeoff.

        Returns
        -------
        list[str]
            Human-readable warning messages. Empty list means the mission is valid.
        """
        warnings: list[str] = []
        has_takeoff = False
        has_land_before_takeoff = False

        for block in blocks:
            if block.name in MissionValidator.CONTROL_BLOCKS:
                continue

            if block.name == "Takeoff":
                has_takeoff = True
                continue

            if block.name == "Land":
                if not has_takeoff:
                    has_land_before_takeoff = True
                    warnings.append(
                        f"Step #{block.execution_order}: Land appears before Takeoff. "
                        "A Takeoff must occur first."
                    )
                continue

            if block.block_type in MissionValidator.MOVEMENT_TYPES and not has_takeoff:
                warnings.append(
                    f"Step #{block.execution_order} – \"{block.name}\": "
                    "Takeoff is required before any movement command."
                )

        return warnings
