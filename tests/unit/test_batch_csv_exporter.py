"""Unit tests for BatchCsvExporter."""

import csv
import io
from collections.abc import Callable
from pathlib import Path

from kuka_value.exporters.batch_csv_exporter import BatchCsvExporter
from kuka_value.models.axis_load import AxisLoad
from kuka_value.models.batch_result import BatchItemResult
from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.payload import Vector3D
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLog


def _rows(content_bytes: bytes) -> list[list[str]]:
    text = content_bytes.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def _section_rows(rows: list[list[str]], is_header: Callable[[list[str]], bool]) -> list[list[str]]:
    """Rows belonging to a table section, bounded by its header row
    (matched via `is_header`) and the next blank separator line."""
    header_idx = next(i for i, r in enumerate(rows) if r and is_header(r))
    end_idx = next((i for i in range(header_idx + 1, len(rows)) if not rows[i]), len(rows))
    return rows[header_idx + 1 : end_idx]


def _summary_rows(rows: list[list[str]]) -> list[list[str]]:
    return _section_rows(rows, lambda r: r[0] == "Backup Name" and len(r) == 6)


def _payload_rows(rows: list[list[str]]) -> list[list[str]]:
    return _section_rows(rows, lambda r: r[0] == "Backup Name" and r[2:3] == ["Index(es)"])


def _axis_load_rows(rows: list[list[str]]) -> list[list[str]]:
    return _section_rows(rows, lambda r: r[0] == "Backup Name" and r[2:3] == ["Axis"])


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
        assert summary[0] == ["TestBackup", "KR 240 R2900", "2", "0", "1", "OK"]

    def test_summary_marks_failure(self, sample_batch_results: list[BatchItemResult]) -> None:
        rows = _rows(BatchCsvExporter().export(sample_batch_results))
        summary = _summary_rows(rows)
        failed_row = summary[2]
        assert failed_row[0] == "BrokenBackup"
        assert failed_row[1] == "-"
        assert "FAILED" in failed_row[5]
        assert "Invalid ZIP file" in failed_row[5]

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

    def test_axis_load_table_empty_when_none_present(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        rows = _rows(BatchCsvExporter().export(sample_batch_results))
        assert _axis_load_rows(rows) == []

    def test_axis_load_table_prefixed_with_backup_and_model(self) -> None:
        robot = RobotInfo(
            model="KR 240 R2900",
            general=GeneralInfo(backup_name="WithAxisLoad"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            axis_loads=[
                AxisLoad(axis=3, mass=12.5, center_of_gravity=Vector3D(x=50.0, y=0.0, z=0.0))
            ],
            warnings=WarningLog(),
        )
        results = [BatchItemResult(source_path=Path("WithAxisLoad"), robot=robot, error=None)]

        rows = _rows(BatchCsvExporter().export(results))
        axis_rows = _axis_load_rows(rows)

        assert len(axis_rows) == 1
        assert axis_rows[0][0] == "WithAxisLoad"
        assert axis_rows[0][1] == "KR 240 R2900"
        assert axis_rows[0][2] == "3"  # axis number
        assert axis_rows[0][3] == "12.5"  # mass

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
