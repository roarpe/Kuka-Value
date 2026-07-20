"""Unit tests for BatchJsonExporter."""

import json
from pathlib import Path

from kuka_value.exporters.batch_json_exporter import BatchJsonExporter
from kuka_value.models.axis_load import AxisLoad
from kuka_value.models.batch_result import BatchItemResult
from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.payload import Vector3D
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLog


class TestBatchJsonExport:
    def test_export_returns_valid_json_array(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        result = BatchJsonExporter().export(sample_batch_results)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_successful_item_has_full_robot_fidelity(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        data = json.loads(BatchJsonExporter().export(sample_batch_results))
        first = data[0]

        assert first["succeeded"] is True
        assert first["error"] is None
        assert first["display_name"] == "TestBackup"
        assert first["model"] == "KR 240 R2900"
        assert len(first["payloads"]) == 2
        assert first["payloads"][0]["mass"] == 10.5
        assert len(first["warnings"]) == 1

    def test_failed_item_has_no_robot_fields(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        data = json.loads(BatchJsonExporter().export(sample_batch_results))
        failed = data[2]

        assert failed["succeeded"] is False
        assert failed["error"] == "Invalid ZIP file"
        assert failed["display_name"] == "BrokenBackup"
        assert "model" not in failed
        assert "payloads" not in failed

    def test_successful_item_includes_axis_loads(self) -> None:
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

        data = json.loads(BatchJsonExporter().export(results))

        assert len(data[0]["axis_loads"]) == 1
        assert data[0]["axis_loads"][0]["axis"] == 3
        assert data[0]["axis_loads"][0]["mass"] == 12.5

    def test_source_path_included_for_all_items(
        self, sample_batch_results: list[BatchItemResult]
    ) -> None:
        data = json.loads(BatchJsonExporter().export(sample_batch_results))
        assert data[0]["source_path"] == "TestBackup"
        assert data[2]["source_path"] == "BrokenBackup.zip"

    def test_empty_results_produces_empty_array(self) -> None:
        result = BatchJsonExporter().export([])
        assert json.loads(result) == []

    def test_export_to_file(
        self, sample_batch_results: list[BatchItemResult], tmp_path: Path
    ) -> None:
        target = tmp_path / "batch.json"
        BatchJsonExporter().export_to_file(sample_batch_results, target)

        assert target.exists()
        assert target.read_bytes() == BatchJsonExporter().export(sample_batch_results)
