"""Unit tests for JsonExporter."""

import json

from kuka_value.exporters.json_exporter import JsonExporter
from kuka_value.models.axis_load import AxisLoad
from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.payload import Vector3D
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLog


class TestJsonExport:
    """Test JSON serialization content."""

    def test_export_returns_valid_json(self, sample_robot_info: RobotInfo) -> None:
        result = JsonExporter().export(sample_robot_info)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_export_top_level_fields(self, sample_robot_info: RobotInfo) -> None:
        data = json.loads(JsonExporter().export(sample_robot_info))

        assert data["model"] == "KR 240 R2900"
        assert data["general"]["backup_name"] == "TestBackup"
        assert data["general"]["kss_version"] == "8.6.8"
        assert data["controller"]["controller_type"] == "KRC4"
        assert data["controller"]["serial_number"] == "12345"

    def test_export_payload_full_fidelity(self, sample_robot_info: RobotInfo) -> None:
        data = json.loads(JsonExporter().export(sample_robot_info))

        first = data["payloads"][0]
        assert first["mass"] == 10.5
        assert first["center_of_gravity"] == {"x": 100.0, "y": 0.0, "z": 50.0}
        assert first["inertia"] == {"x": 0.5, "y": 0.5, "z": 0.3}
        assert first["indices"] == [1, 3]
        assert first["source_file"] == "$config.dat"

    def test_export_payload_without_inertia_is_null(self, sample_robot_info: RobotInfo) -> None:
        data = json.loads(JsonExporter().export(sample_robot_info))

        second = data["payloads"][1]
        assert second["inertia"] is None

    def test_export_warnings_included(self, sample_robot_info: RobotInfo) -> None:
        data = json.loads(JsonExporter().export(sample_robot_info))

        assert len(data["warnings"]) == 1
        warning = data["warnings"][0]
        assert warning["level"] == "WARNING"
        assert warning["source"] == "PayloadAnalyzer"
        assert "incompleto" in warning["message"].lower()

    def test_export_empty_payloads_list(self) -> None:
        robot = RobotInfo(
            model="UNKNOWN",
            general=GeneralInfo(backup_name="Empty"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            payloads=[],
            warnings=WarningLog(),
        )
        data = json.loads(JsonExporter().export(robot))

        assert data["payloads"] == []
        assert data["axis_loads"] == []
        assert data["warnings"] == []

    def test_export_axis_load_full_fidelity(self) -> None:
        robot = RobotInfo(
            model="KR 240 R2900",
            general=GeneralInfo(backup_name="Test"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            axis_loads=[
                AxisLoad(
                    axis=3,
                    mass=12.5,
                    center_of_gravity=Vector3D(x=50.0, y=0.0, z=0.0),
                    inertia=Vector3D(x=0.1, y=0.2, z=0.3),
                    source_file="$config.dat",
                )
            ],
            warnings=WarningLog(),
        )
        data = json.loads(JsonExporter().export(robot))

        first = data["axis_loads"][0]
        assert first["axis"] == 3
        assert first["mass"] == 12.5
        assert first["center_of_gravity"] == {"x": 50.0, "y": 0.0, "z": 0.0}
        assert first["inertia"] == {"x": 0.1, "y": 0.2, "z": 0.3}
        assert first["source_file"] == "$config.dat"

    def test_export_axis_load_without_inertia_is_null(self) -> None:
        robot = RobotInfo(
            model="KR 240 R2900",
            general=GeneralInfo(backup_name="Test"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            axis_loads=[
                AxisLoad(axis=1, mass=5.0, center_of_gravity=Vector3D(x=0.0, y=0.0, z=0.0))
            ],
            warnings=WarningLog(),
        )
        data = json.loads(JsonExporter().export(robot))

        assert data["axis_loads"][0]["inertia"] is None

    def test_export_null_optional_fields(self) -> None:
        robot = RobotInfo(
            model="UNKNOWN",
            general=GeneralInfo(backup_name="Empty"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            payloads=[],
            warnings=WarningLog(),
        )
        data = json.loads(JsonExporter().export(robot))

        assert data["general"]["kss_version"] is None
        assert data["controller"]["serial_number"] is None

    def test_export_unicode_round_trips(self) -> None:
        robot = RobotInfo(
            model="UNKNOWN",
            general=GeneralInfo(backup_name="Célula_Soldadura"),
            controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
            payloads=[],
            warnings=WarningLog(),
        )
        result = JsonExporter().export(robot)
        data = json.loads(result)

        assert data["general"]["backup_name"] == "Célula_Soldadura"
        # ensure_ascii=False: non-ASCII stored literally, not \uXXXX escaped
        assert "Célula_Soldadura".encode() in result
