"""Unit tests for BatchCsvExporter."""

import csv
import io
from pathlib import Path

from kuka_value.exporters.batch_csv_exporter import BatchCsvExporter
from kuka_value.models.batch_result import BatchItemResult


def _rows(content_bytes: bytes) -> list[list[str]]:
    text = content_bytes.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def _summary_rows(rows: list[list[str]]) -> list[list[str]]:
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "Backup Name")
    end_idx = next(i for i in range(header_idx, len(rows)) if not rows[i])
    return rows[header_idx + 1 : end_idx]


def _payload_rows(rows: list[list[str]]) -> list[list[str]]:
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "Backup Name" and len(r) > 5)
    return rows[header_idx + 1 :]


class TestBatchCsvExport:
    def test_export_returns_bytes(self, sample_batch_results: list[BatchItemResult]) -> None:
        result = BatchCsvExporter().export(sample_batch_results)
        assert isinstance(result, bytes)

    def test_summary_has_one_row_per_backup(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        rows = _rows(BatchCsvExporter().export(sample_batch_results))
        summary = _summary_rows(rows)
        assert len(summary) == 3

    def test_summary_marks_success_as_ok(self, sample_batch_results: list[BatchItemResult]) -> None:
        rows = _rows(BatchCsvExporter().export(sample_batch_results))
        summary = _summary_rows(rows)
        assert summary[0] == ["TestBackup", "KR 240 R2900", "2", "1", "OK"]

    def test_summary_marks_failure(self, sample_batch_results: list[BatchItemResult]) -> None:
        rows = _rows(BatchCsvExporter().export(sample_batch_results))
        summary = _summary_rows(rows)
        failed_row = summary[2]
        assert failed_row[0] == "BrokenBackup"
        assert failed_row[1] == "-"
        assert "FAILED" in failed_row[4]
        assert "Invalid ZIP file" in failed_row[4]

    def test_payload_table_excludes_failed_backup(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        rows = _rows(BatchCsvExporter().export(sample_batch_results))
        payload_rows = _payload_rows(rows)
        # 2 payloads from TestBackup + 1 from SecondBackup = 3, none from BrokenBackup
        assert len(payload_rows) == 3
        backup_names = {r[0] for r in payload_rows}
        assert backup_names == {"TestBackup", "SecondBackup"}

    def test_payload_row_prefixed_with_backup_and_model(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        rows = _rows(BatchCsvExporter().export(sample_batch_results))
        payload_rows = _payload_rows(rows)
        second_backup_row = next(r for r in payload_rows if r[0] == "SecondBackup")
        assert second_backup_row[1] == "KR 6 R900"
        assert second_backup_row[3] == "5.0"  # mass

    def test_empty_results_produces_empty_tables(self) -> None:
        rows = _rows(BatchCsvExporter().export([]))
        summary = _summary_rows(rows)
        assert summary == []

    def test_export_to_file(
        self, sample_batch_results: list[BatchItemResult], tmp_path: Path
    ) -> None:
        target = tmp_path / "batch.csv"
        BatchCsvExporter().export_to_file(sample_batch_results, target)

        assert target.exists()
        assert target.read_bytes() == BatchCsvExporter().export(sample_batch_results)
