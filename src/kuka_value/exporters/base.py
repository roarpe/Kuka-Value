"""Shared exporter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from kuka_value.models.robot_info import RobotInfo


class Exporter(ABC):
    """Common interface for all export formats.

    Concrete exporters only implement `export()`, returning serialized
    bytes; `export_to_file()` is provided for free.
    """

    @abstractmethod
    def export(self, robot: RobotInfo) -> bytes:
        """Serialize a robot analysis result.

        Args:
            robot: Analysis result to export

        Returns:
            Serialized content as bytes
        """
        raise NotImplementedError

    def export_to_file(self, robot: RobotInfo, path: Path) -> None:
        """Serialize and write directly to a file.

        Args:
            robot: Analysis result to export
            path: Destination file path
        """
        path.write_bytes(self.export(robot))
