"""Result of analyzing one backup within a batch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kuka_value.models.robot_info import RobotInfo


@dataclass(frozen=True)
class BatchItemResult:
    """Outcome of analyzing a single backup as part of a batch.

    Exactly one of `robot`/`error` is set: a batch isolates per-item
    failures (corrupt ZIP, missing path) so one bad backup doesn't
    abort the rest of the batch.
    """

    source_path: Path
    robot: RobotInfo | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.robot is not None

    @property
    def display_name(self) -> str:
        """A human-readable name, even for a backup that failed to parse."""
        if self.robot is not None:
            return self.robot.general.backup_name
        if self.source_path.suffix.lower() == ".zip":
            return self.source_path.stem
        return self.source_path.name
