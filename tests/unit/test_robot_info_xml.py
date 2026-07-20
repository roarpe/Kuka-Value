"""Unit tests for the shared RobotInfo.xml parser."""

import tempfile
from pathlib import Path

import pytest

from kuka_value.analyzers.robot_info_xml import find_robot_info_xml
from kuka_value.parser.backup_reader import BackupReader


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _write_robot_info_xml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestFindRobotInfoXml:
    def test_finds_file_at_real_backup_path(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "C" / "KRC" / "Roboter" / "Rdc" / "RobotInfo.xml"
        _write_robot_info_xml(
            xml_path,
            "<Root><RobotType>#KR240R2900 ULTRA C4 FLR</RobotType>"
            "<SerialNumber>626925</SerialNumber></Root>",
        )

        reader = BackupReader(temp_dir)
        data = find_robot_info_xml(reader)

        assert data is not None
        assert data.robot_type == "#KR240R2900 ULTRA C4 FLR"
        assert data.serial_number == "626925"

    def test_finds_file_regardless_of_nesting_depth(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "some" / "other" / "path" / "robotinfo.xml"
        _write_robot_info_xml(xml_path, "<Root><RobotType>KR6R900</RobotType></Root>")

        reader = BackupReader(temp_dir)
        data = find_robot_info_xml(reader)

        assert data is not None
        assert data.robot_type == "KR6R900"

    def test_filename_match_is_case_insensitive(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "ROBOTINFO.XML"
        _write_robot_info_xml(xml_path, "<Root><SerialNumber>12345</SerialNumber></Root>")

        reader = BackupReader(temp_dir)
        data = find_robot_info_xml(reader)

        assert data is not None
        assert data.serial_number == "12345"

    def test_only_robot_type_present(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "RobotInfo.xml"
        _write_robot_info_xml(xml_path, "<Root><RobotType>KR6R900</RobotType></Root>")

        reader = BackupReader(temp_dir)
        data = find_robot_info_xml(reader)

        assert data is not None
        assert data.robot_type == "KR6R900"
        assert data.serial_number is None

    def test_only_serial_number_present(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "RobotInfo.xml"
        _write_robot_info_xml(xml_path, "<Root><SerialNumber>999</SerialNumber></Root>")

        reader = BackupReader(temp_dir)
        data = find_robot_info_xml(reader)

        assert data is not None
        assert data.robot_type is None
        assert data.serial_number == "999"

    def test_tolerates_xml_namespace(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "RobotInfo.xml"
        _write_robot_info_xml(
            xml_path,
            '<Root xmlns="http://example.com/kuka">' "<RobotType>KR6R900</RobotType></Root>",
        )

        reader = BackupReader(temp_dir)
        data = find_robot_info_xml(reader)

        assert data is not None
        assert data.robot_type == "KR6R900"

    def test_no_file_returns_none(self, temp_dir: Path) -> None:
        reader = BackupReader(temp_dir)
        assert find_robot_info_xml(reader) is None

    def test_malformed_xml_returns_none(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "RobotInfo.xml"
        _write_robot_info_xml(xml_path, "<Root><Unclosed>")

        reader = BackupReader(temp_dir)
        assert find_robot_info_xml(reader) is None

    def test_empty_tags_return_none_data(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "RobotInfo.xml"
        _write_robot_info_xml(xml_path, "<Root><RobotType></RobotType></Root>")

        reader = BackupReader(temp_dir)
        assert find_robot_info_xml(reader) is None

    def test_whitespace_only_tag_treated_as_empty(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "RobotInfo.xml"
        _write_robot_info_xml(xml_path, "<Root><RobotType>   </RobotType></Root>")

        reader = BackupReader(temp_dir)
        assert find_robot_info_xml(reader) is None

    def test_irrelevant_xml_without_recognized_tags_returns_none(self, temp_dir: Path) -> None:
        xml_path = temp_dir / "RobotInfo.xml"
        _write_robot_info_xml(xml_path, "<Root><SomethingElse>value</SomethingElse></Root>")

        reader = BackupReader(temp_dir)
        assert find_robot_info_xml(reader) is None
