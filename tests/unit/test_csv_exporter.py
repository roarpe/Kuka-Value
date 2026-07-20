"""Unit tests for CsvExporter."""

import csv
import io
from pathlib import Path

from kuka_value.exporters.csv_exporter import CsvExporter
from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLog


def _rows(content_bytes: bytes) -> list[list[str]]:
    text = content_bytes.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def _payload_rows(rows: list[list[str]]) -> list[list[str]]:
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "Index(es)")
    return rows[header_idx + 1 :]


class TestCsvExport:
    """Test CSV serialization content."""

    def test_export_returns_bytes(self, sample_robot_info: RobotInfo) -> None:
        result = CsvExporter().export(sample_robot_info)
        assert isinstance(result, bytes)

    def test_export_has_utf8_bom(self, sample_robot_info: RobotInfo) -> None:
        result = CsvExporter().export(sample_robot_info)
        assert result.startswith(b"\xef\xbb\xbf")

    def test_export_contains_model_metadata(self, sample_robot_info: RobotInfo) -> None:
        rows = _rows(CsvExporter().export(sample_robot_info))
        assert ["Model", "KR 240 R2900"] in rows
        assert ["Backup Name", "TestBackup"] in rows
        assert ["KSS Version", "8.6.8"] in rows
        assert ["Controller Type", "KRC4"] in rows
        assert ["Serial Number", "12345"] in rows

    def test_export_contains_payload_rows(self, sample_robot_info: RobotInfo) -> None:
        rows = _rows(CsvExporter().export(sample_robot_info))
        payload_rows = _payload_rows(rows)

        assert len(payload_rows) == 2

    def test_export_payload_values(self, sample_robot_info: RobotInfo) -> None:
        rows = _rows(CsvExporter().export(sample_robot_info))
        payload_rows = _payload_rows(rows)

        first = payload_rows[0]
        assert first[0] == "1, 3"  # merged indices
        assert first[1] == "10.5"  # mass
        assert first[2] == "100.0"  # CoG X
        assert first[5] == "0.5"  # inertia X

    def test_export_missing_inertia_is_blank(self, sample_robot_info: RobotInfo) -> None:
        rows = _rows(CsvExporter().export(sample_robot_info))
        payload_rows = _payload_rows(rows)

        second = payload_rows[1]
        assert second[1] == "25.0"
        assert second[5] == ""  # inertia X blank
        assert second[6] == ""  # inertia Y blank
        assert second[7] == ""  # inertia Z blank

    def test_export_source_file_included(self, sample_robot_info: RobotInfo) -> None:
        rows = _rows(CsvExporter().export(sample_robot_info))
        payload_rows = _payload_rows(rows)

        assert payload_rows[0][8] == "$config.dat"

    def test_export_empty_payloads_still_valid(self) -> None:
        robot = RobotInfo(
            model="UNKNOWN",
            general=GeneralInfo(backup_name="Empty"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            payloads=[],
            warnings=WarningLog(),
        )
        rows = _rows(CsvExporter().export(robot))
        payload_rows = _payload_rows(rows)

        assert payload_rows == []

    def test_export_warning_count(self, sample_robot_info: RobotInfo) -> None:
        rows = _rows(CsvExporter().export(sample_robot_info))
        assert ["Warnings", "1"] in rows


class TestExportToFile:
    """Test the inherited export_to_file() convenience method."""

    def test_export_to_file_writes_content(
        self, sample_robot_info: RobotInfo, tmp_path: Path
    ) -> None:
        target = tmp_path / "output.csv"
        CsvExporter().export_to_file(sample_robot_info, target)

        assert target.exists()
        content = target.read_bytes()
        assert content == CsvExporter().export(sample_robot_info)
