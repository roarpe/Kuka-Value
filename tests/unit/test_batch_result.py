"""Unit tests for BatchItemResult."""

from pathlib import Path

from kuka_value.models.batch_result import BatchItemResult
from kuka_value.models.controller_info import ControllerInfo, ControllerType
from kuka_value.models.general_info import GeneralInfo
from kuka_value.models.robot_info import RobotInfo
from kuka_value.models.warnings import WarningLog


def _robot(backup_name: str = "TestBackup") -> RobotInfo:
    return RobotInfo(
        model="KR 240 R2900",
        general=GeneralInfo(backup_name=backup_name),
        controller=ControllerInfo(controller_type=ControllerType.UNKNOWN),
        payloads=[],
        warnings=WarningLog(),
    )


class TestSucceeded:
    def test_true_when_robot_is_set(self) -> None:
        result = BatchItemResult(source_path=Path("backup"), robot=_robot(), error=None)
        assert result.succeeded is True

    def test_false_when_error_is_set(self) -> None:
        result = BatchItemResult(source_path=Path("backup"), robot=None, error="boom")
        assert result.succeeded is False


class TestDisplayName:
    def test_uses_robot_backup_name_when_present(self) -> None:
        result = BatchItemResult(
            source_path=Path("some/weird/path"), robot=_robot("MyRobot"), error=None
        )
        assert result.display_name == "MyRobot"

    def test_derives_from_zip_stem_when_failed(self) -> None:
        result = BatchItemResult(
            source_path=Path("C:/backups/Robot1.zip"), robot=None, error="Invalid ZIP file"
        )
        assert result.display_name == "Robot1"

    def test_derives_from_folder_name_when_failed(self) -> None:
        result = BatchItemResult(
            source_path=Path("C:/backups/Robot2"), robot=None, error="not found"
        )
        assert result.display_name == "Robot2"
