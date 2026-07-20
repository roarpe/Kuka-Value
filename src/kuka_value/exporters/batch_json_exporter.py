"""JSON export for a batch of robot analysis results."""

from __future__ import annotations

import json
from typing import Any

from kuka_value.exporters.batch_base import BatchExporter
from kuka_value.exporters.json_exporter import JsonExporter
from kuka_value.models.batch_result import BatchItemResult


class BatchJsonExporter(BatchExporter):
    """Exports a batch of results as a JSON array, one entry per backup.

    Full-fidelity, including failed items (source_path + error, no
    robot data) - unlike CSV/Excel, nothing about a failure is
    dropped, since this format targets programmatic consumption.
    """

    def export(self, results: list[BatchItemResult]) -> bytes:
        data = [self._item_dict(r) for r in results]
        return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _item_dict(result: BatchItemResult) -> dict[str, Any]:
        if result.robot is None:
            return {
                "source_path": str(result.source_path),
                "display_name": result.display_name,
                "succeeded": False,
                "error": result.error,
            }
        return {
            "source_path": str(result.source_path),
            "display_name": result.display_name,
            "succeeded": True,
            "error": None,
            **JsonExporter.robot_dict(result.robot),
        }
