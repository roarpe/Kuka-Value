"""CSV export for a batch of robot analysis results."""

from __future__ import annotations

import csv
import io

from kuka_value.exporters.batch_base import BatchExporter
from kuka_value.exporters.csv_exporter import PAYLOAD_HEADERS, CsvExporter
from kuka_value.models.batch_result import BatchItemResult

_SUMMARY_HEADERS = ["Backup Name", "Model", "Payloads", "Warnings", "Status"]


class BatchCsvExporter(BatchExporter):
    """Exports a batch of results as a single CSV.

    Layout: a summary table (one row per backup, including failures),
    a blank separator line, then one combined payload table across
    all successfully analyzed backups (Backup Name/Model prefixed to
    each row so payloads stay attributable after flattening).
    """

    def export(self, results: list[BatchItemResult]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(_SUMMARY_HEADERS)
        for result in results:
            writer.writerow(self._summary_row(result))
        writer.writerow([])

        writer.writerow(["Backup Name", "Model", *PAYLOAD_HEADERS])
        for result in results:
            if result.robot is None:
                continue
            for payload in result.robot.payloads:
                writer.writerow(
                    [result.display_name, result.robot.model, *CsvExporter.payload_row(payload)]
                )

        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def _summary_row(result: BatchItemResult) -> list[str | int]:
        if result.robot is None:
            return [result.display_name, "-", 0, 0, f"FAILED: {result.error}"]
        return [
            result.display_name,
            result.robot.model,
            len(result.robot.payloads),
            len(result.robot.warnings),
            "OK",
        ]
