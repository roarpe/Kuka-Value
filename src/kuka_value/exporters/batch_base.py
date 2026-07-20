"""Shared contract for batch (multi-backup) exporters.

Separate from Exporter(ABC): a batch exporter consumes
list[BatchItemResult], not a single RobotInfo, so it isn't
substitutable for a single-backup exporter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from kuka_value.models.batch_result import BatchItemResult


class BatchExporter(ABC):
    """Common interface for exporters that consolidate multiple backups."""

    @abstractmethod
    def export(self, results: list[BatchItemResult]) -> bytes:
        """Serialize a batch of analysis results.

        Args:
            results: One result per analyzed backup, in any order

        Returns:
            Serialized content as bytes
        """
        raise NotImplementedError

    def export_to_file(self, results: list[BatchItemResult], path: Path) -> None:
        """Serialize and write directly to a file.

        Args:
            results: One result per analyzed backup
            path: Destination file path
        """
        path.write_bytes(self.export(results))
